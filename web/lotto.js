// Ядро веб-версии (iPhone). Построчный перенос lotto_core.py: те же правила
// игр, частоты, генерация, проверка билетов. Сверяется с Python тестом
// tests/test_web_core.py — расхождение валит сборку.
(function (root) {
  "use strict";

  const MAX_50_FROM = "2019-05-14";
  const MAX_52_FROM = "2026-04-14";
  const DRAW_WEEKDAYS = { "649": [3, 6], LOTTOMAX: [2, 5] }; // 0 — воскресенье (JS)
  const WEEKDAY_RU = ["воскресенье", "понедельник", "вторник", "среда", "четверг",
                      "пятница", "суббота"];
  const LINE_PRICE = { LOTTOMAX: 1.5, "649": 3.0 };

  function maxBall(gameKey, day) {
    if (gameKey === "LOTTOMAX") {
      if (!day || day >= MAX_52_FROM) return 52;
      if (day >= MAX_50_FROM) return 50;
      return 49;
    }
    return 49;
  }

  function comb(n, k) {
    let r = 1;
    for (let i = 1; i <= k; i++) r = (r * (n - k + i)) / i;
    return Math.round(r);
  }

  // ------------------------------------------------------------ даты
  function iso(d) {
    const z = (x) => String(x).padStart(2, "0");
    return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}`;
  }
  function parseIso(s) {
    const [y, m, d] = s.split("-").map(Number);
    return new Date(y, m - 1, d);
  }
  function ru(s) {
    const [y, m, d] = s.split("-");
    return `${d}.${m}.${y}`;
  }
  function nextDraw(gameKey, todayIso) {
    const d = parseIso(todayIso);
    while (!DRAW_WEEKDAYS[gameKey].includes(d.getDay())) d.setDate(d.getDate() + 1);
    return iso(d);
  }

  // ------------------------------------------------------------ статистика
  function erfc(x) {
    // Абрамовиц–Стиган 7.1.26, точность ~1e-7 — для p-значения достаточно.
    const z = Math.abs(x);
    const t = 1 / (1 + 0.5 * z);
    const r = t * Math.exp(-z * z - 1.26551223 + t * (1.00002368 + t * (0.37409196 +
      t * (0.09678418 + t * (-0.18628806 + t * (0.27886807 + t * (-1.13520398 +
      t * (1.48851587 + t * (-0.82215223 + t * 0.17087277)))))))));
    return x >= 0 ? r : 2 - r;
  }
  function chi2sf(x, k) {
    if (x <= 0 || k <= 0) return 1;
    const z = (Math.cbrt(x / k) - (1 - 2 / (9 * k))) / Math.sqrt(2 / (9 * k));
    return 0.5 * erfc(z / Math.SQRT2);
  }

  // draws: [[iso, [числа], бонус], ...] по возрастанию даты
  function computeStats(gameKey, pick, draws) {
    let top = maxBall(gameKey);
    if (draws.length) top = Math.max(...draws.map((d) => maxBall(gameKey, d[0])));
    else top = maxBall(gameKey);
    const counts = {}, last = {}, expected = {};
    for (let n = 1; n <= top; n++) { counts[n] = 0; expected[n] = 0; }
    draws.forEach((d, i) => {
      for (const n of d[1]) { counts[n] += 1; last[n] = i; }
      const t = maxBall(gameKey, d[0]);
      for (let n = 1; n <= t; n++) expected[n] += pick / t;
    });
    const total = draws.length;
    const numbers = {};
    for (let n = 1; n <= top; n++) {
      numbers[n] = { number: n, count: counts[n], share: total ? counts[n] / total : 0,
        since: n in last ? total - 1 - last[n] : null };
    }
    let chi2 = 0;
    for (let n = 1; n <= top; n++) {
      if (expected[n] > 0) chi2 += (counts[n] - expected[n]) ** 2 / expected[n];
    }
    const expAvg = Object.values(expected).reduce((a, b) => a + b, 0) / top;
    return { gameKey, pick, draws, top, numbers, expected: expAvg, chi2,
             p: total ? chi2sf(chi2, top - 1) : 1 };
  }

  function ranked(stats, reverse = true) {
    return Object.values(stats.numbers).sort((a, b) =>
      reverse ? b.count - a.count || a.number - b.number
              : a.count - b.count || b.number - a.number);
  }

  // ------------------------------------------------------------ популярные
  function popularReasons(ticket) {
    const t = [...ticket].sort((a, b) => a - b);
    const out = [];
    if (t.filter((n) => n > 31).length < 2) out.push("почти все числа — дни месяца (1–31)");
    let run = 1, best = 1;
    for (let i = 1; i < t.length; i++) {
      run = t[i] === t[i - 1] + 1 ? run + 1 : 1;
      best = Math.max(best, run);
    }
    if (best >= 3) out.push(`${best} числа подряд`);
    const s = new Set(t);
    outer: for (let i = 0; i < t.length - 3; i++) {
      for (let j = i + 1; j < t.length - 2; j++) {
        const step = t[j] - t[i];
        if (step > 1 && [0, 1, 2, 3].every((k) => s.has(t[i] + k * step))) {
          out.push(`«лесенка» с шагом ${step}`);
          break outer;
        }
      }
    }
    const tails = {};
    for (const n of t) tails[n % 10] = (tails[n % 10] || 0) + 1;
    if (Math.max(...Object.values(tails)) >= 4) out.push("4 и больше чисел с одной последней цифрой");
    return out;
  }

  // ------------------------------------------------------------ генерация
  const STRATEGIES = {
    hot: "Чаще выпадавшие (с учётом веса)",
    top: "Строго самые частые",
    cold: "Реже выпадавшие (с учётом веса)",
    overdue: "Давно не выпадавшие",
    mix: "Смесь: половина частых, половина редких",
    random: "Полностью случайно",
  };

  function weightedSample(pool, w, k, rnd) {
    pool = [...pool];
    const out = [];
    while (pool.length && out.length < k) {
      const ws = pool.map((n) => Math.max(w[n] || 0, 1e-9));
      let r = rnd() * ws.reduce((a, b) => a + b, 0);
      let i = 0;
      while (i < ws.length - 1 && (r -= ws[i]) > 0) i++;
      out.push(pool[i]);
      pool.splice(i, 1);
    }
    return out;
  }

  function generate(stats, strategy, tickets, opts = {}) {
    const rnd = opts.rnd || Math.random;
    const pick = stats.pick;
    const all = Object.keys(stats.numbers).map(Number);
    const fixed = new Set((opts.fixed || []).filter((n) => n in stats.numbers));
    const excluded = new Set((opts.excluded || []).filter((n) => !fixed.has(n)));
    if (fixed.size > pick) throw new Error(`Закреплено ${fixed.size} чисел, а в билете только ${pick}.`);
    const pool = all.filter((n) => !fixed.has(n) && !excluded.has(n));
    const need = pick - fixed.size;
    if (pool.length < need) throw new Error("Слишком много исключённых чисел — не из чего выбрать.");
    const strength = opts.strength ?? 1;
    const counts = {};
    for (const n of all) counts[n] = stats.numbers[n].count;
    const mean = all.reduce((a, n) => a + counts[n], 0) / all.length || 1;
    const hotW = () => Object.fromEntries(pool.map((n) => [n, ((counts[n] + 1) / (mean + 1)) ** (strength * 4)]));
    const coldW = (p) => Object.fromEntries(p.map((n) => [n, ((mean + 1) / (counts[n] + 1)) ** (strength * 4)]));
    const overdueW = () => Object.fromEntries(pool.map((n) => {
      const s = stats.numbers[n].since;
      return [n, (1 + (s === null ? stats.draws.length : s)) ** (strength * 2)];
    }));
    const seen = new Set((opts.avoid || []).map((t) => [...t].sort((a, b) => a - b).join(",")));
    const result = [];
    let attempts = 0;
    const maxAttempts = tickets * (opts.avoidPopular ? 200 : 50);
    while (result.length < tickets && attempts < maxAttempts) {
      attempts++;
      let part;
      if (strategy === "top") {
        const r = [...pool].sort((a, b) => counts[b] - counts[a] || a - b);
        const start = (attempts - 1) * need;
        part = r.slice(start, start + need);
        if (part.length < need) part = weightedSample(pool, hotW(), need, rnd);
      } else if (strategy === "hot") part = weightedSample(pool, hotW(), need, rnd);
      else if (strategy === "cold") part = weightedSample(pool, coldW(pool), need, rnd);
      else if (strategy === "overdue") part = weightedSample(pool, overdueW(), need, rnd);
      else if (strategy === "mix") {
        const hk = Math.floor((need + 1) / 2);
        part = weightedSample(pool, hotW(), hk, rnd);
        const rest = pool.filter((n) => !part.includes(n));
        part = part.concat(weightedSample(rest, coldW(rest), need - hk, rnd));
      } else if (strategy === "random") part = weightedSample(pool, {}, need, rnd);
      else throw new Error("Неизвестный способ: " + strategy);
      const ticket = [...new Set([...fixed, ...part])].sort((a, b) => a - b);
      const key = ticket.join(",");
      if (seen.has(key)) continue;
      if (opts.avoidPopular && popularReasons(ticket).length) continue;
      seen.add(key);
      result.push(ticket);
    }
    return result;
  }

  // ------------------------------------------------------------ билеты
  function prize(gameKey, pick, m, bonus) {
    if (m === pick) return "ДЖЕКПОТ";
    if (gameKey === "LOTTOMAX") {
      if (m >= 4 || (m === 3 && bonus)) return "денежный приз (сумму смотрите на сайте)";
      if (m === 3) return "бесплатный билет";
    } else {
      if (m >= 3 || (m === 2 && bonus)) return "денежный приз (сумму смотрите на сайте)";
      if (m === 2) return "бесплатный билет";
    }
    return "";
  }

  function checkTicket(gameKey, pick, numbers, drawDay, draws, extras = []) {
    const main = draws.find((d) => d[0] === drawDay);
    if (!main) return { drawn: false, text: "ждёт тиража" };
    const t = new Set(numbers);
    const m = main[1].filter((n) => t.has(n)).length;
    const bonus = main[2] !== null && main[2] !== undefined && t.has(main[2]);
    const mm = extras.filter((d) => d[0] === drawDay && d[1].length === t.size &&
                                    d[1].every((n) => t.has(n))).length;
    const pz = prize(gameKey, pick, m, bonus);
    let text = `${m} из ${pick}` + (bonus ? " + бонус" : "") + (pz ? ` — ${pz}` : " — без приза");
    if (mm) text += `; MaxMillions совпал целиком: ${mm}!`;
    return { drawn: true, matches: m, bonus, prize: pz, maxmillions: mm, text };
  }

  function parseNumbers(text, gameKey, pick, day) {
    const nums = (text.match(/\d+/g) || []).map(Number);
    const top = maxBall(gameKey, day);
    if (nums.length !== pick) throw new Error(`Нужно ${pick} чисел, а введено ${nums.length}.`);
    if (new Set(nums).size !== nums.length) throw new Error("Числа в билете не должны повторяться.");
    const bad = nums.filter((n) => n < 1 || n > top);
    if (bad.length) throw new Error(`Числа должны быть от 1 до ${top}: не подходит ${bad.join(", ")}.`);
    return nums.sort((a, b) => a - b);
  }

  // ------------------------------------------------------------ деньги
  function ticketCost(t) { return Number(t.cost ?? LINE_PRICE[t.game] ?? 0); }

  function moneySummary(items, todayIso) {
    const today = parseIso(todayIso);
    const ws = new Date(today);
    ws.setDate(ws.getDate() - ((today.getDay() + 6) % 7)); // понедельник
    const weekStart = iso(ws);
    const month = todayIso.slice(0, 7);
    const out = { week: 0, month: 0, total: 0, won: 0 };
    for (const t of items) {
      if (!t.bought) continue;
      const c = ticketCost(t), w = Number(t.won || 0);
      out.total += c; out.won += w;
      if (t.bought >= weekStart) out.week += c;
      if (t.bought.slice(0, 7) === month) out.month += c;
    }
    return out;
  }

  // ------------------------------------------------------------ бэктест
  function backtest(gameKey, pick, draws, strategies, last = 300, perDraw = 10, rnd = Math.random) {
    const start = Math.max(1, draws.length - last);
    const counts = {}, lastSeen = {};
    for (let i = 0; i < start; i++) for (const n of draws[i][1]) { counts[n] = (counts[n] || 0) + 1; lastSeen[n] = i; }
    const acc = Object.fromEntries(strategies.map((s) => [s, [0, 0, 0, 0]]));
    // Разброс — по средним за тираж: билеты одного способа похожи друг на друга
    // (см. lotto_core.backtest), считать их независимыми нельзя.
    const means = Object.fromEntries(strategies.map((s) => [s, []]));
    let expSum = 0;
    const steps = draws.length - start;
    for (let i = start; i < draws.length; i++) {
      const top = maxBall(gameKey, draws[i][0]);
      const numbers = {};
      for (let n = 1; n <= top; n++) {
        const c = counts[n] || 0;
        numbers[n] = { number: n, count: c, share: c / i,
          since: n in lastSeen ? i - 1 - lastSeen[n] : null };
      }
      const st = { gameKey, pick, draws: { length: i }, top, numbers };
      expSum += pick * pick / top;
      const win = new Set(draws[i][1]);
      for (const s of strategies) {
        const ts = generate(st, s, perDraw, { rnd });
        let got = 0;
        for (const t of ts) {
          const m = t.filter((n) => win.has(n)).length;
          const a = acc[s];
          a[0]++; a[1] += m; a[2] += m >= 3; a[3] += m >= 4; got += m;
        }
        if (ts.length) means[s].push(got / ts.length);
      }
      for (const n of draws[i][1]) { counts[n] = (counts[n] || 0) + 1; lastSeen[n] = i; }
    }
    const exp = steps ? expSum / steps : 0;
    const seOf = (xs) => {
      const n = xs.length;
      if (n < 2) return 0;
      const mu = xs.reduce((a, b) => a + b, 0) / n;
      return Math.sqrt(xs.reduce((a, x) => a + (x - mu) ** 2, 0) / (n - 1) / n);
    };
    return strategies.map((s) => {
      const a = acc[s];
      const avg = a[0] ? a[1] / a[0] : 0, se = seOf(means[s]);
      return { strategy: s, tickets: a[0], avg, hits3: a[2], hits4: a[3], expected: exp, se,
               z: se ? (avg - exp) / se : 0 };
    });
  }

  const api = { MAX_50_FROM, MAX_52_FROM, WEEKDAY_RU, LINE_PRICE, STRATEGIES, maxBall, comb,
    iso, parseIso, ru, nextDraw, chi2sf, computeStats, ranked, popularReasons, generate,
    prize, checkTicket, parseNumbers, ticketCost, moneySummary, backtest };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Lotto = api;
})(this);
