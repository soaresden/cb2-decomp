#!/usr/bin/env node
// Apply skins (.cb2skin.json, made with the web site's Prêt-à-porter) to a Cool Boarders 2 disc, with or without the
// Remix, and turn an image into a custom board on a memory card. Same code as the site (cb2.js, menu.js, board.js,
// disc.js are loaded from a checkout of the CB2Remix repository), so the result matches "Créer le jeu modifié".
//
//   node skins/cb2skins.js jeu.chd --remix --skin a.cb2skin.json --skin b.cb2skin.json -o "CB2 Remix perso.chd"
//   node skins/cb2skins.js jeu.chd --board planche.png [--board-bottom dessous.png] [--card carte.srm] -o carte.srm
//
// Options: --site <dir> (CB2Remix checkout, default ../CB2Remix next to this repo), --style 0-2, --type 0-2
'use strict';
const fs = require('fs'), path = require('path'), zlib = require('zlib');

function args() {
  const a = process.argv.slice(2), o = { skins: [], site: path.join(__dirname, '..', '..', 'CB2Remix'), style: 0, type: 0 };
  for (let i = 0; i < a.length; i++) {
    const k = a[i], v = () => a[++i];
    if (k === '--skin') o.skins.push(v()); else if (k === '--remix') o.remix = true; else if (k === '-o') o.out = v();
    else if (k === '--site') o.site = v(); else if (k === '--board') o.board = v(); else if (k === '--board-bottom') o.boardBottom = v();
    else if (k === '--card') o.card = v(); else if (k === '--style') o.style = +v(); else if (k === '--type') o.type = +v();
    else if (k === '-h' || k === '--help') o.help = true; else if (!o.src) o.src = k; else throw new Error('argument inconnu : ' + k);
  }
  return o;
}

// ---- minimal PNG decoder (8-bit grey / RGB / RGBA / palette, non interlaced): what canvas.toDataURL and image editors write
function decodePNG(buf) {
  if (buf.readUInt32BE(0) !== 0x89504e47) throw new Error('pas une image PNG');
  let o = 8, w, h, depth, ct, il, pal = null, trns = null; const idat = [];
  while (o < buf.length) {
    const len = buf.readUInt32BE(o), type = buf.toString('latin1', o + 4, o + 8), d = buf.subarray(o + 8, o + 8 + len); o += 12 + len;
    if (type === 'IHDR') { w = d.readUInt32BE(0); h = d.readUInt32BE(4); depth = d[8]; ct = d[9]; il = d[12]; }
    else if (type === 'PLTE') pal = d; else if (type === 'tRNS') trns = d; else if (type === 'IDAT') idat.push(d); else if (type === 'IEND') break;
  }
  if (depth !== 8 || il) throw new Error('PNG non géré (8 bits non entrelacé seulement) : enregistre-le à nouveau en PNG 8 bits');
  const bpp = { 0: 1, 2: 3, 3: 1, 4: 2, 6: 4 }[ct], raw = zlib.inflateSync(Buffer.concat(idat)), stride = w * bpp;
  const px = Buffer.alloc(h * stride); let prev = Buffer.alloc(stride);
  for (let y = 0; y < h; y++) {
    const f = raw[y * (stride + 1)], line = raw.subarray(y * (stride + 1) + 1, (y + 1) * (stride + 1)), cur = px.subarray(y * stride, (y + 1) * stride);
    for (let i = 0; i < stride; i++) {
      const a = i >= bpp ? cur[i - bpp] : 0, b = prev[i], c = i >= bpp ? prev[i - bpp] : 0; let v = line[i];
      if (f === 1) v += a; else if (f === 2) v += b; else if (f === 3) v += (a + b) >> 1;
      else if (f === 4) { const p = a + b - c, pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c); v += pa <= pb && pa <= pc ? a : pb <= pc ? b : c; }
      cur[i] = v & 255;
    }
    prev = cur;
  }
  const rgba = new Uint8ClampedArray(w * h * 4);
  for (let i = 0; i < w * h; i++) {
    let r, g, b, al = 255;
    if (ct === 0) r = g = b = px[i]; else if (ct === 4) { r = g = b = px[i * 2]; al = px[i * 2 + 1]; }
    else if (ct === 2) { r = px[i * 3]; g = px[i * 3 + 1]; b = px[i * 3 + 2]; }
    else if (ct === 6) { r = px[i * 4]; g = px[i * 4 + 1]; b = px[i * 4 + 2]; al = px[i * 4 + 3]; }
    else { const k = px[i]; r = pal[k * 3]; g = pal[k * 3 + 1]; b = pal[k * 3 + 2]; al = trns && k < trns.length ? trns[k] : 255; }
    rgba.set([r, g, b, al], i * 4);
  }
  return { w, h, rgba };
}
// bilinear resize ("cover": fill the target, centred crop) of an RGBA image onto a white background
function cover(img, W, H) {
  const out = new Uint8ClampedArray(W * H * 4), s = Math.max(W / img.w, H / img.h), ox = (img.w - W / s) / 2, oy = (img.h - H / s) / 2;
  const at = (x, y, c) => img.rgba[(Math.min(img.h - 1, Math.max(0, y)) * img.w + Math.min(img.w - 1, Math.max(0, x))) * 4 + c];
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const fx = ox + (x + 0.5) / s - 0.5, fy = oy + (y + 0.5) / s - 0.5, x0 = Math.floor(fx), y0 = Math.floor(fy), dx = fx - x0, dy = fy - y0;
    const px = [0, 1, 2, 3].map((c) => at(x0, y0, c) * (1 - dx) * (1 - dy) + at(x0 + 1, y0, c) * dx * (1 - dy) + at(x0, y0 + 1, c) * (1 - dx) * dy + at(x0 + 1, y0 + 1, c) * dx * dy);
    const al = px[3] / 255; for (let c = 0; c < 3; c++) out[(y * W + x) * 4 + c] = px[c] * al + 255 * (1 - al); out[(y * W + x) * 4 + 3] = 255;
  }
  return out;
}

async function openDisc(Disc, file) {
  const fd = fs.openSync(file, 'r'), size = fs.fstatSync(fd).size;
  const read = async (a, b) => { const buf = Buffer.alloc(b - a); fs.readSync(fd, buf, 0, b - a, a); return new Uint8Array(buf); };
  return { d: await Disc.open(read, size, path.basename(file)), read };
}
function remixLoc(exe) { // Remix extras (competition textures of Gray / Snowman), null on a non-Remix exe (same as app.js)
  const o = 0x800 + 0x8004f900 - 0x80010000, bcd = (b) => (b >> 4) * 10 + (b & 15);
  const L = ['gray', 'snow', 'eg', 'es'].reduce((m, k, i) => { const p = o + i * 8; const lba = (bcd(exe[p]) * 60 + bcd(exe[p + 1])) * 75 + bcd(exe[p + 2]) - 150; m[k] = { lba, size: exe[p + 4] | (exe[p + 5] << 8) | (exe[p + 6] << 16) }; return m; }, {});
  return L.eg.size ? L : null;
}

async function main() {
  const o = args();
  if (o.help || !o.src) { console.log(fs.readFileSync(__filename, 'utf8').split('\n').slice(1, 9).map((l) => l.replace(/^\/\/ ?/, '')).join('\n')); return; }
  const need = (f) => { const p = path.join(o.site, f); if (!fs.existsSync(p)) throw new Error('introuvable : ' + p + ' (indique le dossier du site avec --site)'); return require(p); };
  const Disc = need('disc.js'), CB2 = need('cb2.js'), MenuSkin = need('menu.js'), Board = need('board.js');
  const { d } = await openDisc(Disc, o.src); const TW = CB2.TW, TH = CB2.TH;
  if (!d.files['/DATA/CHR/FR/1P/FRM1.PMD']) throw new Error("ce disque n'est pas Cool Boarders 2");

  if (o.board) {   // ---- custom board -> memory card
    const img = new Uint8ClampedArray(Board.W * Board.H * 4);
    const top = decodePNG(fs.readFileSync(o.board));
    if (o.boardBottom) { img.set(cover(top, Board.W, 32), 0); img.set(cover(decodePNG(fs.readFileSync(o.boardBottom)), Board.W, 32), Board.W * 32 * 4); }
    else img.set(top.w === Board.W && top.h === Board.H ? top.rgba : cover(top, Board.W, Board.H));   // 128x64 = the site's "Exporter PNG"
    const header = Board.header(await d.readFile('/SCES_009.92'));
    const card = o.card ? new Uint8Array(fs.readFileSync(o.card)) : Board.newCard();
    if (!Board.cardOK(card)) throw new Error("ce n'est pas une carte mémoire PS1 de 128 Ko");
    const out = Board.writeFile(card, Board.NAME, Board.encode(img, o.style, o.type, header));
    fs.writeFileSync(o.out || 'carte.srm', out); console.log('Carte mémoire écrite :', o.out || 'carte.srm');
    if (!o.skins.length && !o.remix) return;
  }

  // ---- disc: Remix and/or skins (same steps as app.js "Créer le jeu modifié")
  let sec = {}, chr0 = null;
  const user = async (l) => (sec[l] ? (sec[l] instanceof Uint8Array ? sec[l] : sec[l].data) : d.user(l));
  const putFile = async (lba, bytes) => { for (let k = 0; k < Math.ceil(bytes.length / 2048); k++) { const u = (await user(lba + k)).slice(); u.set(bytes.subarray(k * 2048, Math.min(bytes.length, (k + 1) * 2048)));
    sec[lba + k] = sec[lba + k] && !(sec[lba + k] instanceof Uint8Array) ? { sub: sec[lba + k].sub, data: u } : u; } };
  const readF = async (p) => { const e = d.files[p], out = new Uint8Array(Math.ceil(e.size / 2048) * 2048); for (let k = 0; k < out.length / 2048; k++) out.set(await user(e.lba + k), k * 2048); return out.subarray(0, e.size); };
  if (o.remix) {
    const js = fs.readFileSync(path.join(o.site, 'patches.js'), 'utf8'), m = js.match(/delta:\s*'([^']+)'/), ver = (js.match(/version:\s*'([^']+)'/) || [])[1];
    const P = new Uint8Array(zlib.gunzipSync(Buffer.from(m[1], 'base64')));
    try { sec = await d.applyDelta(P); } catch (e) { throw new Error(e.code === 'source' ? "le Remix s'installe sur le jeu d'origine : ce disque est déjà modifié" : e.message); }
    console.log('Remix v' + ver);
  }
  const loc = remixLoc(await readF('/SCES_009.92'));
  try { chr0 = await readF('/TITLE/CHR.DAT'); } catch (e) { chr0 = null; }
  const menu = chr0 ? MenuSkin.scan(chr0) : null, models = {}, slots = [];
  for (const f of o.skins) {
    const j = JSON.parse(fs.readFileSync(f, 'utf8'));
    if (j.format !== 'cb2skin') throw new Error(f + " : ce n'est pas un skin Cool Boarders 2");
    const r = CB2.RIDERS.find((x) => x.id === j.rider), s = r && r.slots.find((x) => x.id === j.slot);
    if (!s) throw new Error(f + ' : tenue inconnue ' + j.slot);
    const png = decodePNG(Buffer.from(j.png.split(',')[1], 'base64'));
    if (png.w !== TW || png.h !== TH) throw new Error(f + ' : image de skin de taille inattendue');
    if (!models[r.model]) { const prims = CB2.readPMD(await readF(r.model)); models[r.model] = { prims, pm: CB2.palMap(prims) }; }
    const m = models[r.model], fbd = CB2.readFBD(await readF(s.file)), orig = CB2.toRGBA(fbd, m.pm);
    slots.push({ r, s, m, f: fbd, orig, over: png.rgba, name: j.name });
  }
  const composite = (sl) => { const out = new Uint8ClampedArray(sl.orig);
    for (let i = 0; i < TW * TH; i++) if (sl.over[i * 4 + 3] && sl.m.pm[i] >= 0) { out[i * 4] = sl.over[i * 4]; out[i * 4 + 1] = sl.over[i * 4 + 1]; out[i * 4 + 2] = sl.over[i * 4 + 2]; out[i * 4 + 3] = 255; }
    return out; };
  for (const x of slots) {
    const ch = new Uint8Array(TW * TH); for (let i = 0; i < TW * TH; i++) ch[i] = x.over[i * 4 + 3] ? 1 : 0;
    const bytes = CB2.writeFBD(CB2.fromRGBA(x.f, x.m.pm, composite(x), ch)); await putFile(d.files[x.s.file].lba, bytes);
    console.log('skin :', x.name, '->', x.r.name, x.s.id);
    if (x.s.enemy && loc) { const e = loc[x.s.enemy]; const raw = new Uint8Array(Math.ceil(e.size / 2048) * 2048); for (let k = 0; k < raw.length / 2048; k++) raw.set(await user(e.lba + k), k * 2048);
      await putFile(e.lba, CB2.patchEnemy(raw.subarray(0, e.size), bytes)); console.log('  + texture de compétition'); }
  }
  // menu (WEAR / BOARDER screen) textures of the 4 regular riders
  const RIDX = (r) => CB2.RIDERS.indexOf(r), menuSlot = (sl) => (menu && RIDX(sl.r) < 4 && sl.s.lab[0] === 'combo' ? { r: RIDX(sl.r), j: sl.s.lab[1] - 1, p: sl.s.lab[2] - 1 } : null);
  const maps = {};
  const menuTextures = (r, j, p, list) => { let up = MenuSkin.timRGBA(chr0, menu[r].up[j]), lo = MenuSkin.timRGBA(chr0, menu[r].lo[p]);
    for (const sl of list) { const ms = menuSlot(sl); if (!ms || ms.r !== r) continue; const map = maps[r] || (maps[r] = MenuSkin.buildMap(chr0, r, sl.m.prims));
      const res = MenuSkin.apply(map.map, up, lo, sl.over, sl.orig); if (ms.j === j) up = res.up; if (ms.p === p) lo = res.lo; }
    return { up, lo }; };
  if (menu) {
    const chr = chr0.slice(); let touched = false; const dirty = slots.filter(menuSlot);
    for (let r = 0; r < 4; r++) {
      const mine = dirty.filter((y) => menuSlot(y).r === r); if (!mine.length) continue;
      for (const j of new Set(mine.map((y) => menuSlot(y).j))) MenuSkin.writeTIM(chr, menu[r].up[j], menuTextures(r, j, 0, mine.filter((y) => menuSlot(y).j === j)).up, Board.quant);
      for (const p of new Set(mine.map((y) => menuSlot(y).p))) MenuSkin.writeTIM(chr, menu[r].lo[p], menuTextures(r, 0, p, mine.filter((y) => menuSlot(y).p === p)).lo, Board.quant);
      touched = true;
    }
    if (touched) { await putFile(d.files['/TITLE/CHR.DAT'].lba, chr); console.log('textures du menu mises à jour'); }
  }
  if (!Object.keys(sec).length) { console.log('rien à faire (ajoute --remix et/ou --skin)'); return; }
  const out = o.out || (o.src.replace(/\.(chd|bin)$/i, '') + (o.remix ? ' (Remix)' : '') + ' (skins).' + d.kind);
  const r = await d.build(sec, (m) => console.log(m));
  const fd = fs.openSync(out + '.part', 'w'), src = fs.openSync(o.src, 'r');
  for (const p of r.parts) {
    if (p instanceof Uint8Array) { fs.writeSync(fd, p); continue; }
    for (let a = p.a; a < p.b;) { const n = Math.min(1 << 22, p.b - a), buf = Buffer.alloc(n); fs.readSync(src, buf, 0, n, a); fs.writeSync(fd, buf); a += n; }
  }
  fs.closeSync(fd); fs.renameSync(out + '.part', out); console.log('Écrit :', out);
}
if (require.main === module) main().catch((e) => { console.error('Erreur : ' + e.message); process.exit(1); });
else module.exports = { decodePNG, cover };
