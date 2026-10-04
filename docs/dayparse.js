/* FoxPaths "type your day" reader.
   Turns a sentence like "leave home 10-11am, lunch at Uptown 30-45 min, study at UW 3h+, home by 7pm"
   into a start, stops and an end. Rule-based, no AI: it looks for times, durations, day words and place names.
   parseDay(text, ctx) -> {start, end, day, reorder, goalLabel, acts:[...], ignored:[...]}
   ctx = {places:[{id,n,sub,cat,x,y}], cats:{cat:label}, now:Date} */
(function (root) {
  'use strict';

  // ---------------------------------------------------------------- durations
  const UNIT = '(h|hr|hrs|hour|hours|m|min|mins|minute|minutes)';
  const toMin = (n, u) => Math.round(parseFloat(n) * (/^h/.test(u) ? 60 : 1));

  // "30-45m", "3h+", "1h30", "2h", "45 min", "1-2 hours", "at least 3 hours", "up to 30m"
  // returns {min, max} (max null = no limit) and the matched text, or null
  function findDuration(s) {
    const tries = [
      // 1h30-2h, 1h30m-2h
      [new RegExp(`(\\d+)\\s*h\\s*(\\d+)\\s*m?(?:in(?:ute)?s?)?\\s*-\\s*(\\d+)\\s*h(?:\\s*(\\d+)\\s*m?)?`), m => ({ min: +m[1] * 60 + +m[2], max: +m[3] * 60 + (+m[4] || 0) })],
      // 20-30 min, 1-2 hours, 1.5-2h
      [new RegExp(`(\\d+(?:\\.\\d+)?)\\s*-\\s*(\\d+(?:\\.\\d+)?)\\s*${UNIT}\\b`), m => ({ min: toMin(m[1], m[3]), max: toMin(m[2], m[3]) })],
      // at least 3 hours / 3h+ / 3+ hours / 3 hours or more / minimum 3h
      [new RegExp(`(?:at least|min(?:imum)?|over)\\s*(\\d+(?:\\.\\d+)?)\\s*${UNIT}\\b`), m => ({ min: toMin(m[1], m[2]), max: null })],
      [new RegExp(`(\\d+(?:\\.\\d+)?)\\s*(?:\\+\\s*${UNIT}\\b|${UNIT}\\s*\\+|${UNIT}\\s*(?:or more|plus)\\b)`), m => ({ min: toMin(m[1], m[2] || m[3] || m[4]), max: null })],
      [/(\d+)\s*h\s*(\d+)\s*(?:m(?:in(?:ute)?s?)?)?\s*\+/, m => ({ min: +m[1] * 60 + +m[2], max: null })],
      // up to 30 min / at most 1h / max 45m / no more than an hour
      [new RegExp(`(?:up to|at most|max(?:imum)?|no more than|under)\\s*(\\d+(?:\\.\\d+)?)\\s*${UNIT}\\b`), m => { const x = toMin(m[1], m[2]); return { min: Math.round(x / 2), max: x }; }],
      // 1h30 / 1h 30m / 1 hour 30 minutes
      [/(\d+)\s*(?:h|hr|hrs|hours?)\s*(\d+)\s*(?:m|min|mins|minutes?)?\b/, m => { const x = +m[1] * 60 + +m[2]; return { min: x, max: x }; }],
      // 45 min / 2h / 1.5 hours
      [new RegExp(`(\\d+(?:\\.\\d+)?)\\s*${UNIT}\\b`), m => { const x = toMin(m[1], m[2]); return { min: x, max: x }; }],
      // words
      [/\b(?:half an hour|half hour|30ish)\b/, () => ({ min: 30, max: 30 })],
      [/\b(?:an|one) hour\b/, () => ({ min: 60, max: 60 })],
      [/\b(?:a )?couple(?: of)? hours\b/, () => ({ min: 120, max: 120 })],
      [/\b(?:a )?few hours\b/, () => ({ min: 180, max: null })],
      [/\bquick(?:ly)?\b/, () => ({ min: 10, max: 20 })],
    ];
    for (const [re, f] of tries) {
      const m = s.match(re);
      if (m) {
        const d = f(m);
        if (d.min > 0 || d.max > 0) return { ...d, text: m[0] };
      }
    }
    return null;
  }

  // "3h+" style text for the duration box
  function fmtShort(m) {
    if (m < 60) return m + 'm';
    const h = Math.floor(m / 60), r = m % 60;
    return r ? `${h}h${String(r).padStart(2, '0')}` : `${h}h`;
  }
  function fmtRange(min, max) {
    min = +min || 0;
    if (max === '' || max == null || isNaN(+max)) return min ? fmtShort(min) + '+' : '';
    max = +max;
    if (min === max) return fmtShort(min);
    if (min < 60 && max < 60) return `${min}-${max}m`;
    if (min % 60 === 0 && max % 60 === 0) return `${min / 60}-${max / 60}h`;
    return `${fmtShort(min)}-${fmtShort(max)}`;
  }
  // the duration box accepts the same formats as the sentence reader, plus bare minutes ("45")
  function parseDur(text) {
    const s = String(text || '').toLowerCase().replace(/[–—]/g, '-').replace(/(\d)\s+to\s+(\d)/g, '$1-$2').trim();
    if (!s) return null;
    if (/^\d+$/.test(s)) return { min: +s, max: +s };
    if (/^\d+\s*\+$/.test(s)) return { min: parseInt(s), max: null };
    const d = findDuration(s.replace(/(\d)\s*h(\d)/g, '$1h $2'));
    return d ? { min: d.min, max: d.max } : null;
  }

  // ---------------------------------------------------------------- times
  const TIME = '(noon|midnight|\\d{1,2}(?::\\d{2})?\\s*(?:am|pm|a\\.m\\.|p\\.m\\.)?)';
  // role decides how to read a bare hour: start/activity -> 7-11 am, 1-6 pm; end -> 1-11 pm
  function readTime(t, role, meridiemHint) {
    t = t.trim().replace(/\./g, '');
    if (t === 'noon') return 720;
    if (t === 'midnight') return 1440;
    const m = t.match(/^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$/);
    if (!m) return null;
    let h = +m[1]; const mm = +(m[2] || 0); const mer = m[3] || meridiemHint;
    if (h > 24 || mm > 59) return null;
    if (mer === 'am') { if (h === 12) h = 0; }
    else if (mer === 'pm') { if (h < 12) h += 12; }
    else if (h < 13) {
      if (role === 'end') { if (h >= 1 && h <= 11) h += 12; }
      else if (h >= 1 && h <= 6) h += 12;
    }
    return h * 60 + mm;
  }
  const merOf = t => (t.match(/(am|pm|a\.m\.|p\.m\.)/) || [])[1]?.replace(/\./g, '');

  // finds a time phrase; returns {kind:'range'|'by'|'after'|'at'|'around', a, b, text}
  function findTime(s, role) {
    let m;
    if ((m = s.match(new RegExp(`(?:between|from)\\s+${TIME}\\s+(?:and|-|until|till)\\s+${TIME}`))) ||
        (m = s.match(new RegExp(`${TIME}\\s*-\\s*${TIME}`)))) {
      const mer2 = merOf(m[2]);
      let a = readTime(m[1], role, merOf(m[1]) || mer2), b = readTime(m[2], role);
      if (a != null && b != null && a > b && !merOf(m[1])) a = readTime(m[1], role, 'am');
      if (a != null && b != null && b >= a) return { kind: 'range', a, b, text: m[0] };
    }
    const one = (word, kind) => {
      const mm = s.match(new RegExp(`\\b(?:${word})\\s+${TIME}`));
      if (!mm) return null;
      const v = readTime(mm[1], role);
      return v == null ? null : { kind, a: v, b: v, text: mm[0] };
    };
    return one('by|before|until|till|no later than', 'by') || one('after|from|no earlier than|starting at|starting', 'after') ||
      one('around|about|ish|roughly', 'around') ||
      (() => { // "at 10", "at 9:30", "10am" on its own
        const mm = s.match(new RegExp(`\\bat\\s+${TIME}`)) || s.match(/\b(\d{1,2}(?::\d{2})?\s*(?:am|pm))\b/) || s.match(/\b(\d{1,2}:\d{2})\b/) || s.match(/\b(noon)\b/);
        if (!mm) return null;
        const v = readTime(mm[1], role);
        return v == null ? null : { kind: 'at', a: v, b: v, text: mm[0] };
      })();
  }
  const hhmm = m => `${String(Math.floor(m / 60) % 24).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`;

  // ---------------------------------------------------------------- places
  const STOP = new Set(['the', 'a', 'an', 'of', 'at', 'in', 'on', 'to', 'near', 'my', 'st', 'rd', 'dr', 'ave', 'street', 'road', 'some', 'somewhere', 'any', 'place', 'and', 'by', 'for']);
  const words = s => String(s || '').toLowerCase().replace(/[^a-z0-9 ]/g, ' ').split(/\s+/).filter(Boolean);
  const keyWords = s => words(s).filter(w => !STOP.has(w));
  const CAT_WORDS = {
    food: ['restaurant', 'restaurants', 'food', 'eat', 'eating', 'lunch', 'dinner', 'breakfast', 'brunch', 'cafe', 'coffee', 'snack'],
    study: ['library', 'libraries', 'study', 'studying', 'campus', 'university', 'school'],
    shop: ['mall', 'shop', 'shopping', 'store'],
    groceries: ['groceries', 'grocery', 'supermarket'],
    work: ['work', 'office', 'job', 'shift'],
    health: ['hospital', 'doctor', 'clinic', 'appointment', 'dentist'],
    transit: ['terminal', 'station'],
  };
  function initials(name) { return keyWords(name.split(',')[0]).map(w => w[0]).join(''); }

  // best place for a piece of text; returns {place, score} or null
  function matchPlace(text, places) {
    const q = words(text).join(' ');
    if (!q) return null;
    const qk = keyWords(text);
    let best = null;
    for (const p of places) {
      const name = words(p.n).join(' ');
      let score = 0;
      if (q === name || q === p.id || (p.aliases || []).includes(q) || (qk.length === 1 && qk[0] === initials(p.n) && qk[0].length >= 2)) score = 1;
      else if (qk.length) {
        const pk = keyWords(p.n + ' ' + (p.sub || '') + ' ' + p.id);
        const hit = qk.filter(w => pk.some(t => t === w || (w.length >= 3 && t.startsWith(w)) || (t.length >= 4 && w.startsWith(t)))).length;
        score = hit / qk.length;
        // the place's own name matters more than its subtitle
        const nk = keyWords(p.n);
        if (score && qk.every(w => nk.some(t => t === w || (w.length >= 3 && t.startsWith(w))))) score += 0.2;
      }
      if (score >= 0.5 && (!best || score > best.score + 1e-9 || (Math.abs(score - best.score) < 1e-9 && p._d < best.place._d))) best = { place: p, score };
    }
    return best;
  }
  function categoryOf(text) {
    const w = words(text);
    for (const [cat, list] of Object.entries(CAT_WORDS)) if (w.some(x => list.includes(x))) return cat;
    return null;
  }

  // ---------------------------------------------------------------- clauses
  const DAYS = { sun: 0, mon: 1, tue: 2, wed: 3, thu: 4, fri: 5, sat: 6 };
  function dayType(dow) { return dow === 0 ? 'sunday' : dow === 6 ? 'saturday' : 'weekday'; }

  function parseDay(text, ctx) {
    const places = (ctx.places || []).map(p => ({ ...p }));
    const home = places.find(p => p.id === 'home');
    places.forEach(p => { p._d = home ? Math.hypot(p.x - home.x, p.y - home.y) : 0; });
    const cats = ctx.cats || {};
    const now = ctx.now || new Date();
    const out = { start: null, end: null, day: null, reorder: null, goalLabel: null, acts: [], ignored: [] };

    let s = ' ' + String(text || '').toLowerCase().replace(/[–—]/g, '-').replace(/\s+/g, ' ') + ' ';
    // whole-sentence options
    if (/\b(?:any order|in any order|order doesn'?t matter|flexible order|whatever order)\b/.test(s)) {
      out.reorder = true; s = s.replace(/\b(?:in )?any order\b|\border doesn'?t matter\b|\bflexible order\b|\bwhatever order\b/g, ' ');
    }
    let m;
    if ((m = s.match(/\b(today|tonight|tomorrow|(?:this |next )?(sun|mon|tue|wed|thu|fri|sat)[a-z]*)\b/))) {
      if (m[1] === 'today' || m[1] === 'tonight') out.day = dayType(now.getDay());
      else if (m[1] === 'tomorrow') out.day = dayType((now.getDay() + 1) % 7);
      else if (m[2]) out.day = dayType(DAYS[m[2]]);
      s = s.replace(m[0], ' ');
    }
    if ((m = s.match(/\b(?:most time (?:at|for|on)|maximi[sz]e|as much (?:time )?(?:at|for) )\s*(?:the )?([a-z]+)/))) {
      out.goalLabel = m[1]; s = s.replace(m[0], ' ');
    }

    const clauses = s.split(/[,;\n]|\.\s|\bthen\b|\bafter that\b|\bfollowed by\b|\band\s+(?=(?:then\s+)?[a-z]+\s+(?:at|on|in|near)\b)/)
      .map(c => c.trim().replace(/^(?:and|then|first|finally|after|next)\s+/, '').replace(/\.$/, '').trim()).filter(Boolean);

    for (const raw of clauses) {
      let c = ' ' + raw + ' ';
      const startWords = /\b(?:leave|leaving|start|starting|depart|departing|head out|set off|wake up)\b/.test(c) || /^\s*from\b/.test(c);
      const isEnd = !startWords && (/^\s*(?:go |get |be |head |come )?(?:back )?(?:home|back)\b/.test(c) ||
        /\b(?:end|finish|ending|finishing|done)\b/.test(c) || /\b(?:home|back) (?:by|before|around|between|at|for)\b/.test(c));
      const isStart = !isEnd && startWords;
      const role = isEnd ? 'end' : isStart ? 'start' : 'act';
      const t = findTime(c, role);
      if (t) c = c.replace(t.text, ' ');
      let dur = role === 'act' ? findDuration(c) : null;
      if (dur) c = c.replace(dur.text, ' ');
      const part = role === 'act' && !dur && c.match(/\b(?:all|the whole|the rest of the)\s+(morning|afternoon|evening|day)\b/);
      if (part) {
        dur = { morning: { min: 120, max: null, by: '12:00' }, afternoon: { min: 180, max: null, after: '12:00' },
                evening: { min: 120, max: null, after: '17:00' }, day: { min: 300, max: null } }[part[1]];
        c = c.replace(part[0], ' ');
      }
      c = c.replace(/\s+/g, ' ').trim();

      if (role === 'start' || role === 'end') {
        let placeText = '';
        const pm = c.match(/\b(?:from|at|leave|leaving|start(?:ing)?(?: from| at)?|depart(?:ing)?(?: from)?|end(?:ing)?(?: at)?|finish(?:ing)?(?: at)?|back (?:at|to)|get (?:back )?to|go (?:back )?to)\s+(.+)$/);
        if (pm) placeText = pm[1];
        else if (/\bhome\b/.test(c) || /\bback\b/.test(c)) placeText = 'home';
        placeText = placeText.replace(/\b(?:by|before|around|between|at)\b.*$/, '').trim();
        const mp = placeText ? (placeText === 'home' ? { place: places.find(p => p.id === 'home') } : matchPlace(placeText, places)) : null;
        const w = { text: raw };
        if (mp && mp.place) w.place = mp.place.id;
        else if (!placeText) w.place = 'home';
        else if (placeText && placeText !== 'home') w.placeText = placeText;
        if (t) {
          if (role === 'start') {
            const [a, b] = t.kind === 'range' ? [t.a, t.b] : t.kind === 'by' ? [t.a - 60, t.a] : t.kind === 'after' ? [t.a, t.a + 60] : t.kind === 'around' ? [t.a - 15, t.a + 15] : [t.a, t.a + 15];
            w.from = hhmm(Math.max(0, a)); w.to = hhmm(b);
          } else {
            const [a, b] = t.kind === 'range' ? [t.a, t.b] : t.kind === 'by' ? [t.a - 60, t.a] : t.kind === 'after' ? [t.a, t.a + 120] : [t.a - 15, t.a + 15];
            w.from = hhmm(Math.max(0, a)); w.to = hhmm(Math.min(1439, b));
          }
        }
        out[role] = w;
        continue;
      }

      // a stop: "<what> at <where>"
      const act = { text: raw, label: '', place: null, placeText: '', min: dur ? dur.min : null, max: dur ? dur.max : null, after: (dur && dur.after) || '', by: (dur && dur.by) || '' };
      if (t) {
        if (t.kind === 'range') { act.after = hhmm(t.a); act.by = hhmm(t.b); }
        else if (t.kind === 'by') act.by = hhmm(t.a);
        else act.after = hhmm(Math.max(0, t.kind === 'around' ? t.a - 15 : t.a));
      }
      let what = c, where = '';
      const pm = c.match(/^(.*?)\b(?:at|on|in|near|to|@)\s+(.+)$/);
      if (pm) { what = pm[1].trim(); where = pm[2].trim(); }
      what = what.replace(/^(?:go|going|head|then|i want to|want to|i'd like to|i need to|need to|have|grab|get|do some|do)\s+/, '').trim();
      // "kfc 30m" with no preposition: try the whole thing as a place
      if (!where) {
        const mp = matchPlace(what, places);
        if (mp && mp.score >= 0.99) { where = what; what = ''; }
        else if (!categoryOf(what)) { where = what; }
      }
      const cleanWhere = where.replace(/^(?:the|a|an|some)\s+/, '').trim();
      const cat = categoryOf(cleanWhere) || (!cleanWhere ? categoryOf(what) : null);
      const anyWord = /^(?:a|an|any|some|somewhere|a nearby|nearby)\b/.test(where) || !cleanWhere;
      let mp = cleanWhere ? matchPlace(cleanWhere, places.filter(p => p.cat !== 'home' || /home/.test(cleanWhere))) : null;
      if (mp && mp.score < 0.7 && cat && anyWord) mp = null;
      if (mp) act.place = mp.place.id;
      else if (cat && anyWord && cats[cat]) act.place = 'any:' + cat;
      else if (cat && anyWord) {
        const inCat = places.filter(p => p.cat === cat).sort((a, b) => a._d - b._d);
        if (inCat.length) act.place = inCat[0].id;
      }
      if (!act.place && cleanWhere) act.placeText = cleanWhere;
      what = what.replace(/\s+(?:somewhere|someplace|nearby|anywhere)\b.*$/, '').trim();
      const lab = what || (cleanWhere && !act.place ? cleanWhere : '');
      act.label = lab ? lab.charAt(0).toUpperCase() + lab.slice(1) : '';
      if (!act.label && act.place) {
        const p = places.find(x => x.id === act.place);
        act.label = p ? p.n.split(',')[0] : '';
      }
      if (!act.place && !act.placeText && !dur && !t) { out.ignored.push(raw); continue; }
      out.acts.push(act);
    }
    return out;
  }

  const api = { parseDay, parseDur, fmtRange, fmtShort, findDuration, findTime, matchPlace };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.DayParse = api;
})(typeof window !== 'undefined' ? window : globalThis);
