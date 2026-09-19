// The painting, as stroke geometry in world coordinates.
//
// The world is a 2160x2700 sheet holding four scenes in quadrants. A single
// spine — the "one brushstroke" — threads through all four: it is the pond's
// waterline, then the bamboo stalk, then the crest of the great wave, then
// the ensō, before tailing off toward the signature.

export const WORLD = { w: 2160, h: 2700 }

export const SCENES = [
  { id: 'pond', title: 'the pond', part: 'koi on koto', cam: { x: 600, y: 760 }, accent: '#3f5f9e' },
  { id: 'grove', title: 'the grove', part: 'panda on flute', cam: { x: 1560, y: 760 }, accent: '#5f8f4e' },
  { id: 'wave', title: 'the wave', part: 'octopus on whistle', cam: { x: 600, y: 1940 }, accent: '#1d6f86' },
  { id: 'enso', title: 'the ensō', part: 'cat on music box', cam: { x: 1580, y: 1900 }, accent: '#c8962e' },
]

export const SEAL_POS = { x: 1930, y: 2520 }
export const SIGN_POS = { x: 250, y: 2520 }

// --- small geometry helpers -------------------------------------------------

let SEED = 1
const nextSeed = () => SEED++

/** A stroke. `pts` are control points; everything else is brush behaviour. */
function S(pts, o = {}) {
  return { pts, w: 14, seed: nextSeed(), group: o.group || null, ...o }
}

function arcPts(cx, cy, rx, ry, a0, a1, n = 14, rot = 0) {
  const out = []
  for (let i = 0; i <= n; i++) {
    const a = a0 + ((a1 - a0) * i) / n
    const x = Math.cos(a) * rx
    const y = Math.sin(a) * ry
    out.push([cx + x * Math.cos(rot) - y * Math.sin(rot), cy + x * Math.sin(rot) + y * Math.cos(rot)])
  }
  return out
}

const D = (deg) => (deg * Math.PI) / 180

/** A cluster of bamboo leaves: pointed at both ends, drooping, one flick each. */
function leafCluster(x, y, dir, n, len, group, accent) {
  const out = []
  for (let i = 0; i < n; i++) {
    const a = dir + (i / Math.max(1, n - 1) - 0.5) * 1.15 + 0.34
    const l = len * (0.72 + (0.42 * ((i * 7919) % 13)) / 13)
    const bow = 0.2
    const mx = x + Math.cos(a) * l * 0.55 - Math.sin(a) * l * bow
    const my = y + Math.sin(a) * l * 0.55 + Math.cos(a) * l * bow
    const tinted = i % 3 === 1 && accent
    const rx = x + Math.cos(dir) * i * 9
    const ry = y + Math.sin(dir) * i * 9
    out.push(
      S([[rx, ry], [mx, my], [rx + Math.cos(a) * l, ry + Math.sin(a) * l]], {
        w: 26,
        group,
        taperIn: 0.4,
        taperOut: 0.44,
        dry: 0.12,
        wet: 0.5,
        swell: 0.55,
        pool: [0.45],
        color: tinted ? accent : undefined,
        alpha: tinted ? 0.78 : 1,
      }),
    )
  }
  return out
}

/** Scale a finished set of strokes about a point — used to size the cast. */
function scaleAbout(strokes, cx, cy, k) {
  for (const st of strokes) {
    st.pts = st.pts.map(([x, y]) => [cx + (x - cx) * k, cy + (y - cy) * k])
    st.w *= k
  }
  return strokes
}

// ---------------------------------------------------------------------------
// the spine — one continuous line, split into the pieces the camera visits
// ---------------------------------------------------------------------------

const SPINE_SEGMENTS = [
  // 0: pond waterline
  {
    scene: 0,
    pts: [[80, 762], [262, 720], [458, 744], [664, 712], [860, 738], [1062, 700]],
    w: 20,
    dry: 0.3,
    taperIn: 0.05,
    taperOut: 0.04,
  },
  // 1: the line leaving the pond and climbing into the grove
  { link: true, pts: [[1062, 700], [1180, 618], [1302, 468], [1400, 330], [1430, 262]], w: 15, dry: 0.34 },
  // 2: the bamboo stalk
  {
    scene: 1,
    pts: [[1430, 262], [1452, 500], [1470, 740], [1492, 980], [1512, 1226]],
    w: 40,
    dry: 0.26,
    taperIn: 0.04,
    taperOut: 0.06,
    swell: 0.12,
  },
  // 3: the long fall from the grove to the sea
  { link: true, pts: [[1512, 1226], [1400, 1402], [1150, 1560], [880, 1662], [700, 1720]], w: 15, dry: 0.36 },
  // 4: the crest of the great wave, curling back on itself
  {
    scene: 2,
    pts: [
      [700, 1720], [520, 1698], [340, 1758], [232, 1880], [282, 2012], [424, 2062],
      [566, 2020], [762, 2042], [942, 2000], [1092, 2032],
    ],
    w: 34,
    dry: 0.32,
    taperIn: 0.03,
    taperOut: 0.05,
    swell: 0.25,
  },
  // 5: across to the last scene
  { link: true, pts: [[1092, 2032], [1180, 2062], [1250, 2038], [1289, 2006]], w: 14, dry: 0.34 },
  // 6: the ensō
  {
    scene: 3,
    pts: arcPts(1580, 1900, 310, 310, D(160), D(490), 26),
    w: 46,
    dry: 0.3,
    taperIn: 0.03,
    taperOut: 0.26,
    swell: 0.3,
  },
  // 7: the tail, running out toward the signature
  {
    tail: true,
    pts: [[1381, 2137], [1300, 2262], [1180, 2360], [1058, 2408]],
    w: 13,
    dry: 0.44,
    taperOut: 0.5,
  },
]

export const SPINE = SPINE_SEGMENTS.map((s) =>
  S(s.pts, { w: s.w, dry: s.dry, taperIn: s.taperIn ?? 0.1, taperOut: s.taperOut ?? 0.2, swell: s.swell, wet: 0.7, spine: true, scene: s.scene, link: !!s.link, tail: !!s.tail }),
)

// ---------------------------------------------------------------------------
// scene 1 — the pond, a koi, a frog
// ---------------------------------------------------------------------------

function pond(accent) {
  const g = 'pond'
  const out = []

  // reeds along the left bank
  out.push(S([[188, 950], [168, 820], [150, 690], [136, 604]], { w: 8, group: g, dry: 0.4, taperOut: 0.6 }))
  out.push(S([[214, 962], [216, 842], [230, 726], [248, 650]], { w: 7, group: g, dry: 0.42, taperOut: 0.6 }))
  out.push(S([[150, 930], [120, 850], [92, 790]], { w: 6, group: g, dry: 0.45, taperOut: 0.6 }))

  // lotus pad and its flower
  out.push(S(arcPts(336, 832, 116, 40, D(-170), D(150), 16), { w: 11, group: g, dry: 0.3, wet: 0.8 }))
  out.push(S([[336, 832], [300, 818]], { w: 6, group: g, dry: 0.5 }))
  for (let i = 0; i < 5; i++) {
    const a = D(-150 + i * 30)
    out.push(
      S([[880, 660], [880 + Math.cos(a) * 34, 660 + Math.sin(a) * 40], [880 + Math.cos(a) * 58, 660 + Math.sin(a) * 66]], {
        w: 13,
        group: g,
        color: accent,
        alpha: 0.8,
        taperOut: 0.5,
        swell: 0.4,
      }),
    )
  }
  out.push(S([[880, 664], [884, 704], [890, 740]], { w: 7, group: g, color: accent, alpha: 0.6 }))

  // the koi — one fat tapering body stroke, then the trimmings
  const k = 'koi'
  out.push(
    S([[812, 992], [726, 952], [612, 926], [508, 934], [432, 952]], {
      w: 46,
      group: k,
      dry: 0.2,
      wet: 0.9,
      taperIn: 0.1,
      taperOut: 0.42,
      swell: 0.3,
    }),
  )
  // tail fan
  out.push(S([[440, 950], [372, 906], [316, 868]], { w: 16, group: k, taperOut: 0.6, dry: 0.34, swell: 0.4 }))
  out.push(S([[440, 952], [366, 958], [300, 948]], { w: 18, group: k, taperOut: 0.6, dry: 0.34, swell: 0.4 }))
  out.push(S([[440, 956], [380, 1000], [326, 1032]], { w: 15, group: k, taperOut: 0.6, dry: 0.34, swell: 0.4 }))
  // fins
  out.push(S([[640, 908], [612, 872], [572, 858]], { w: 12, group: k, taperOut: 0.6, dry: 0.3 }))
  out.push(S([[730, 986], [712, 1030], [672, 1050]], { w: 13, group: k, taperOut: 0.6, dry: 0.3 }))
  // face
  out.push(S([[822, 978], [828, 980]], { w: 11, group: k, taperIn: 0.01, taperOut: 0.01, dry: 0 }))
  out.push(S([[818, 1004], [846, 1016], [866, 1010]], { w: 5, group: k, taperOut: 0.6, dry: 0.4 }))
  out.push(S([[816, 1012], [840, 1036], [864, 1042]], { w: 5, group: k, taperOut: 0.6, dry: 0.4 }))
  // accent markings
  out.push(S([[700, 944], [660, 932], [622, 936]], { w: 26, group: k, color: accent, alpha: 0.5, wet: 1.1, dry: 0.15 }))
  out.push(S([[790, 968], [762, 962]], { w: 20, group: k, color: accent, alpha: 0.45, wet: 1.1, dry: 0.15 }))

  // the frog, sitting on the pad
  const f = 'frog'
  out.push(S([[270, 820], [288, 772], [330, 754], [374, 774], [392, 818]], { w: 15, group: f, dry: 0.2, wet: 0.8 }))
  out.push(S(arcPts(302, 764, 17, 15, D(150), D(390), 10), { w: 8, group: f, dry: 0.15 }))
  out.push(S(arcPts(356, 762, 17, 15, D(150), D(390), 10), { w: 8, group: f, dry: 0.15 }))
  out.push(S([[302, 766], [306, 768]], { w: 9, group: f, taperIn: 0.01, taperOut: 0.01, dry: 0 }))
  out.push(S([[356, 764], [360, 766]], { w: 9, group: f, taperIn: 0.01, taperOut: 0.01, dry: 0 }))
  out.push(S([[300, 794], [330, 804], [362, 792]], { w: 6, group: f, dry: 0.3 }))
  out.push(S([[284, 818], [274, 846], [296, 856]], { w: 10, group: f, dry: 0.25 }))
  out.push(S([[380, 818], [390, 846], [368, 856]], { w: 10, group: f, dry: 0.25 }))
  out.push(S([[300, 812], [266, 832], [262, 856]], { w: 12, group: f, dry: 0.3, taperOut: 0.5 }))

  scaleAbout(out.filter((s) => s.group === 'frog'), 330, 806, 1.42)

  // ripples spreading from the koi
  for (let i = 0; i < 3; i++) {
    out.push(
      S(arcPts(600 + i * 60, 706 - i * 8, 130 + i * 78, 22 + i * 8, D(-165), D(-15), 14), {
        w: 5 - i * 0.8,
        group: g,
        color: accent,
        alpha: 0.5 - i * 0.1,
        dry: 0.4,
        wet: 0.3,
      }),
    )
  }
  return out
}

// ---------------------------------------------------------------------------
// scene 2 — the bamboo grove and a panda with a flute
// ---------------------------------------------------------------------------

function grove(accent) {
  const g = 'grove'
  const out = []

  // two companion stalks
  out.push(S([[1252, 120], [1282, 520], [1300, 900], [1320, 1330]], { w: 30, group: g, dry: 0.26, taperIn: 0.02, taperOut: 0.03, swell: 0.08 }))
  out.push(S([[1836, 110], [1808, 500], [1794, 880], [1784, 1300]], { w: 25, group: g, dry: 0.3, taperIn: 0.02, taperOut: 0.03, swell: 0.08 }))

  // nodes
  for (const [x, y, w] of [
    [1440, 400, 46], [1462, 700, 46], [1486, 1000, 48],
    [1282, 470, 32], [1296, 760, 32],
    [1810, 430, 28], [1798, 720, 28],
  ]) {
    out.push(S([[x - w / 2, y + 4], [x, y - 3], [x + w / 2, y + 3]], { w: 7, group: g, dry: 0.2, taperOut: 0.3 }))
  }

  // branches and leaves
  out.push(S([[1452, 440], [1560, 392], [1660, 372]], { w: 8, group: g, dry: 0.4, taperOut: 0.5 }))
  out.push(...leafCluster(1660, 372, D(-22), 6, 120, g, accent))
  out.push(S([[1444, 356], [1352, 318], [1268, 300]], { w: 7, group: g, dry: 0.4, taperOut: 0.5 }))
  out.push(...leafCluster(1268, 300, D(200), 5, 104, g, accent))
  out.push(S([[1472, 780], [1580, 742], [1668, 712]], { w: 7, group: g, dry: 0.42, taperOut: 0.5 }))
  out.push(...leafCluster(1668, 712, D(-14), 5, 96, g, accent))
  out.push(...leafCluster(1812, 300, D(-40), 5, 110, g, accent))
  out.push(...leafCluster(1300, 640, D(196), 4, 88, g, accent))

  // the panda
  const p = 'panda'
  out.push(S(arcPts(1608, 1130, 118, 112, D(-40), D(250), 20), { w: 22, group: p, dry: 0.22, wet: 0.9 }))
  out.push(S(arcPts(1590, 1002, 76, 70, D(120), D(430), 20), { w: 20, group: p, dry: 0.2, wet: 0.9 }))
  // ears
  out.push(S(arcPts(1528, 948, 24, 24, D(0), D(360), 12), { w: 26, group: p, dry: 0.1, wet: 1 }))
  out.push(S(arcPts(1652, 944, 24, 24, D(0), D(360), 12), { w: 26, group: p, dry: 0.1, wet: 1 }))
  // eye patches, slanted inward
  out.push(S(arcPts(1560, 1000, 25, 17, D(0), D(360), 12, D(28)), { w: 20, group: p, dry: 0.12, wet: 1 }))
  out.push(S(arcPts(1624, 998, 25, 17, D(0), D(360), 12, D(-28)), { w: 20, group: p, dry: 0.12, wet: 1 }))
  // nose
  out.push(S([[1588, 1032], [1598, 1034]], { w: 15, group: p, taperIn: 0.02, taperOut: 0.02, dry: 0 }))
  // arms, holding the flute up to the muzzle
  out.push(S([[1520, 1090], [1492, 1058], [1500, 1040]], { w: 34, group: p, dry: 0.16, wet: 0.9, taperOut: 0.35 }))
  out.push(S([[1694, 1084], [1706, 1050], [1690, 1034]], { w: 34, group: p, dry: 0.16, wet: 0.9, taperOut: 0.35 }))
  // legs
  out.push(S([[1544, 1228], [1520, 1250], [1540, 1266]], { w: 40, group: p, dry: 0.16, wet: 0.9, taperOut: 0.3 }))
  out.push(S([[1676, 1226], [1700, 1248], [1680, 1264]], { w: 40, group: p, dry: 0.16, wet: 0.9, taperOut: 0.3 }))
  // the flute
  out.push(S([[1478, 1042], [1580, 1038], [1712, 1030]], { w: 11, group: 'flute', color: accent, dry: 0.18, wet: 0.6 }))
  for (let i = 0; i < 4; i++) {
    out.push(S([[1600 + i * 26, 1032], [1604 + i * 26, 1034]], { w: 6, group: 'flute', taperIn: 0.02, taperOut: 0.02, dry: 0 }))
  }
  scaleAbout(out.filter((s) => s.group === 'panda' || s.group === 'flute'), 1608, 1140, 1.24)

  // grass at the foot of the grove
  for (let i = 0; i < 7; i++) {
    const x = 1300 + i * 100
    out.push(S([[x, 1372], [x + 18 - i * 4, 1300], [x + 30 - i * 7, 1246]], { w: 9, group: g, dry: 0.4, taperOut: 0.62 }))
  }

  return out
}

// ---------------------------------------------------------------------------
// scene 3 — the great wave, an octopus, a crab
// ---------------------------------------------------------------------------

function greatWave(accent) {
  const g = 'wave'
  const out = []

  // foam claws breaking off the curl
  const clawBase = [
    [268, 1826, -120], [318, 1782, -96], [388, 1756, -74], [468, 1744, -58], [556, 1748, -44],
  ]
  for (const [x, y, deg] of clawBase) {
    const a = D(deg)
    out.push(
      S(
        [
          [x, y],
          [x + Math.cos(a) * 46, y + Math.sin(a) * 46],
          [x + Math.cos(a) * 74 + 22, y + Math.sin(a) * 74],
        ],
        { w: 17, group: g, dry: 0.34, taperOut: 0.62, swell: 0.3 },
      ),
    )
  }
  // inner curl lines
  out.push(S(arcPts(352, 1912, 92, 82, D(-40), D(220), 16), { w: 10, group: g, dry: 0.4, color: accent, alpha: 0.8 }))
  out.push(S(arcPts(356, 1918, 52, 46, D(-10), D(230), 14), { w: 7, group: g, dry: 0.42, color: accent, alpha: 0.7 }))

  // troughs
  out.push(S([[240, 2140], [430, 2110], [640, 2136], [860, 2106], [1060, 2130]], { w: 9, group: g, dry: 0.45, color: accent, alpha: 0.6 }))
  out.push(S([[300, 2210], [520, 2186], [760, 2212], [980, 2190]], { w: 7, group: g, dry: 0.5, color: accent, alpha: 0.45 }))

  // a far peak beyond the sea
  out.push(S([[760, 1660], [830, 1596], [900, 1660]], { w: 8, group: g, dry: 0.5, alpha: 0.5, taperOut: 0.5 }))

  // the octopus, riding the crest
  const o = 'octopus'
  out.push(S(arcPts(432, 1838, 74, 66, D(178), D(362), 18), { w: 21, group: o, dry: 0.2, wet: 0.9 }))
  out.push(S([[360, 1840], [380, 1876], [432, 1888], [486, 1876], [504, 1840]], { w: 15, group: o, dry: 0.24 }))
  out.push(S([[404, 1824], [410, 1826]], { w: 13, group: o, taperIn: 0.02, taperOut: 0.02, dry: 0 }))
  out.push(S([[456, 1822], [462, 1824]], { w: 13, group: o, taperIn: 0.02, taperOut: 0.02, dry: 0 }))
  for (let i = 0; i < 6; i++) {
    const t = i / 5
    const x = 366 + t * 136
    const dir = (t - 0.5) * 1.5
    out.push(
      S(
        [
          [x, 1886],
          [x + dir * 34 - 14, 1944],
          [x + dir * 70 + 18, 1982],
          [x + dir * 92 - 10, 2018],
        ],
        { w: 14, group: o, dry: 0.28, taperOut: 0.58, swell: 0.25 },
      ),
    )
  }
  // one tentacle lifts a whistle
  out.push(S([[506, 1866], [560, 1842], [596, 1812]], { w: 13, group: o, dry: 0.26, taperOut: 0.5 }))
  out.push(S([[596, 1806], [630, 1794], [648, 1800]], { w: 15, group: 'whistle', color: accent, dry: 0.15, wet: 0.5 }))
  out.push(S([[612, 1786], [616, 1788]], { w: 7, group: 'whistle', taperIn: 0.02, taperOut: 0.02, dry: 0 }))

  // the crab, on a rock in the shallows
  const c = 'crab'
  out.push(S(arcPts(918, 2188, 96, 34, D(180), D(360), 16), { w: 16, group: g, dry: 0.42, alpha: 0.7 }))
  out.push(S(arcPts(912, 2118, 56, 40, D(174), D(366), 16), { w: 19, group: c, dry: 0.2, wet: 0.9 }))
  out.push(S([[894, 2100], [900, 2102]], { w: 11, group: c, taperIn: 0.02, taperOut: 0.02, dry: 0 }))
  out.push(S([[930, 2100], [936, 2102]], { w: 11, group: c, taperIn: 0.02, taperOut: 0.02, dry: 0 }))
  // claws
  out.push(S([[858, 2110], [816, 2078], [800, 2040]], { w: 15, group: c, dry: 0.24, taperOut: 0.4 }))
  out.push(S([[966, 2110], [1008, 2078], [1024, 2040]], { w: 15, group: c, dry: 0.24, taperOut: 0.4 }))
  // the bamboo blocks it is playing
  out.push(S([[782, 2016], [818, 2008]], { w: 24, group: 'blocks', color: accent, dry: 0.12, wet: 0.6 }))
  out.push(S([[1008, 2016], [1044, 2008]], { w: 24, group: 'blocks', color: accent, dry: 0.12, wet: 0.6 }))
  // legs
  for (let i = 0; i < 3; i++) {
    const y = 2124 + i * 16
    out.push(S([[868, y], [828, y + 22], [812, y + 44]], { w: 8, group: c, dry: 0.3, taperOut: 0.5 }))
    out.push(S([[956, y], [996, y + 22], [1012, y + 44]], { w: 8, group: c, dry: 0.3, taperOut: 0.5 }))
  }

  scaleAbout(out.filter((s) => s.group === 'crab' || s.group === 'blocks'), 912, 2110, 1.22)
  scaleAbout(out.filter((s) => s.group === 'octopus' || s.group === 'whistle'), 440, 1890, 1.14)

  return out
}

// ---------------------------------------------------------------------------
// scene 4 — a cat curled inside the ensō
// ---------------------------------------------------------------------------

function ensoCat(accent) {
  const c = 'cat'
  const out = []

  // the curled back — one long stroke, the way a cat is actually drawn
  out.push(
    S([[1442, 1986], [1470, 1878], [1560, 1822], [1664, 1846], [1716, 1926], [1712, 2010]], {
      w: 40,
      group: c,
      dry: 0.24,
      wet: 0.9,
      taperIn: 0.07,
      taperOut: 0.2,
      swell: 0.2,
    }),
  )
  // the tail, wrapping round to the nose
  out.push(
    S([[1712, 2014], [1668, 2072], [1580, 2086], [1500, 2062], [1466, 2028]], {
      w: 24,
      group: c,
      dry: 0.3,
      taperOut: 0.5,
      swell: 0.35,
    }),
  )
  // head
  out.push(S(arcPts(1476, 1996, 62, 56, D(120), D(430), 20), { w: 20, group: c, dry: 0.2, wet: 0.9 }))
  // ears
  out.push(S([[1436, 1956], [1424, 1912], [1466, 1936]], { w: 14, group: c, dry: 0.18 }))
  out.push(S([[1506, 1942], [1522, 1902], [1536, 1948]], { w: 14, group: c, dry: 0.18 }))
  // sleeping eyes, nose, whiskers
  out.push(S(arcPts(1452, 1992, 15, 11, D(200), D(340), 10), { w: 7, group: c, dry: 0.12 }))
  out.push(S(arcPts(1504, 1988, 15, 11, D(200), D(340), 10), { w: 7, group: c, dry: 0.12 }))
  out.push(S([[1476, 2010], [1482, 2012]], { w: 10, group: c, taperIn: 0.02, taperOut: 0.02, dry: 0 }))
  out.push(S([[1470, 2018], [1440, 2028]], { w: 4, group: c, dry: 0.4, taperOut: 0.6 }))
  out.push(S([[1488, 2018], [1518, 2026]], { w: 4, group: c, dry: 0.4, taperOut: 0.6 }))
  // paws
  out.push(S([[1516, 2044], [1556, 2052], [1590, 2044]], { w: 16, group: c, dry: 0.26, taperOut: 0.4 }))
  // stripes
  out.push(S([[1546, 1846], [1552, 1812]], { w: 11, group: c, dry: 0.3, taperOut: 0.6, alpha: 0.8 }))
  out.push(S([[1612, 1852], [1622, 1822]], { w: 11, group: c, dry: 0.3, taperOut: 0.6, alpha: 0.8 }))
  out.push(S([[1668, 1892], [1694, 1872]], { w: 11, group: c, dry: 0.3, taperOut: 0.6, alpha: 0.8 }))

  // the music box it fell asleep listening to
  const m = 'musicbox'
  out.push(S([[1742, 2096], [1826, 2096]], { w: 15, group: m, color: accent, dry: 0.15, wet: 0.6 }))
  out.push(S([[1748, 2096], [1748, 2064], [1820, 2064], [1820, 2096]], { w: 10, group: m, color: accent, dry: 0.2 }))
  out.push(S([[1826, 2074], [1848, 2066], [1846, 2050]], { w: 8, group: m, color: accent, dry: 0.25, taperOut: 0.4 }))
  // three notes drifting out of it
  for (let i = 0; i < 3; i++) {
    const x = 1790 + i * 30
    const y = 2020 - i * 34
    out.push(S([[x, y], [x + 2, y - 26]], { w: 7, group: m, color: accent, alpha: 0.85, dry: 0.2 }))
    out.push(S(arcPts(x - 5, y + 2, 9, 7, D(0), D(360), 8), { w: 8, group: m, color: accent, alpha: 0.85, dry: 0.2 }))
  }

  scaleAbout(out.filter((s) => s.group === 'cat'), 1572, 1952, 1.3)

  return out
}

// ---------------------------------------------------------------------------

export const SCENE_STROKES = [
  pond(SCENES[0].accent),
  grove(SCENES[1].accent),
  greatWave(SCENES[2].accent),
  ensoCat(SCENES[3].accent),
]

/** Ambient wash / mist / hills per scene, drawn under the strokes. */
export const SCENE_ATMOS = [
  {
    hills: { x: 600, y: 402, w: 980, h: 170 },
    mist: { x: 600, y: 500, w: 1180, h: 90 },
    washes: [
      { x: 600, y: 960, rx: 520, ry: 250, color: 'rgba(63,95,158,0.5)', a: 0.24 },
      { x: 560, y: 790, rx: 440, ry: 90, color: 'rgba(40,44,54,0.4)', a: 0.16 },
    ],
  },
  {
    hills: { x: 1560, y: 380, w: 1000, h: 150 },
    mist: { x: 1560, y: 900, w: 1200, h: 130 },
    washes: [
      { x: 1600, y: 1180, rx: 420, ry: 180, color: 'rgba(95,143,78,0.45)', a: 0.12 },
      { x: 1500, y: 620, rx: 380, ry: 300, color: 'rgba(95,143,78,0.35)', a: 0.06 },
    ],
  },
  {
    hills: { x: 820, y: 1648, w: 900, h: 140 },
    mist: { x: 600, y: 1700, w: 1200, h: 110 },
    washes: [
      { x: 520, y: 2060, rx: 520, ry: 230, color: 'rgba(29,111,134,0.55)', a: 0.28 },
      { x: 330, y: 1930, rx: 200, ry: 200, color: 'rgba(29,111,134,0.5)', a: 0.22 },
    ],
  },
  {
    hills: { x: 1560, y: 1560, w: 900, h: 130 },
    mist: { x: 1580, y: 2260, w: 1100, h: 110 },
    washes: [
      { x: 1580, y: 1920, rx: 300, ry: 290, color: 'rgba(200,150,46,0.4)', a: 0.2 },
      { x: 1560, y: 2060, rx: 260, ry: 120, color: 'rgba(40,44,54,0.35)', a: 0.12 },
    ],
  },
]

/** Every stroke of the painting, in the order the brush lays them down. */
export const ALL_STROKES = [SPINE, ...SCENE_STROKES]
