/* GLSL for the landing scene. Kept unlit and cheap: shapes are SDFs in UV space. */

const rotation = /* glsl */ `
mat3 rotXYZ(vec3 r) {
  float cx = cos(r.x), sx = sin(r.x);
  float cy = cos(r.y), sy = sin(r.y);
  float cz = cos(r.z), sz = sin(r.z);
  mat3 rx = mat3(1., 0., 0., 0., cx, sx, 0., -sx, cx);
  mat3 ry = mat3(cy, 0., -sy, 0., 1., 0., sy, 0., cy);
  mat3 rz = mat3(cz, sz, 0., -sz, cz, 0., 0., 0., 1.);
  return rz * ry * rx;
}
`;

export const cardVertex = /* glsl */ `
uniform float uTime;
uniform float uGather;
attribute vec3 aScatter;
attribute vec3 aStack;
attribute vec3 aRot;
attribute float aSeed;
attribute float aKind;
varying vec2 vUv;
varying float vKind;
varying float vSeed;
varying float vG;
varying float vFade;
varying float vDepth;
${rotation}
void main() {
  // 0 = back of the stack, 1 = front (stack z spans about +-0.3)
  vDepth = clamp(aStack.z / 0.6 + 0.5, 0., 1.);
  // staggered flight: early seeds leave first
  float g = smoothstep(aSeed * 0.5, aSeed * 0.5 + 0.5, uGather);
  g = g * g * (3. - 2. * g);
  float free = 1. - g;
  vec3 drift = vec3(
    sin(uTime * 0.21 + aSeed * 12.) * 0.28,
    cos(uTime * 0.17 + aSeed * 7.) * 0.32,
    sin(uTime * 0.13 + aSeed * 3.) * 0.22
  ) * free;
  vec3 wobble = vec3(sin(uTime * 0.19 + aSeed * 5.) * 0.18, cos(uTime * 0.16 + aSeed * 9.) * 0.22, 0.) * free;
  vec3 rot = mix(aRot + wobble, vec3(-0.06, -0.32, (aSeed - 0.5) * 0.05), g);
  float scale = mix(0.92, 1.45, g);
  vec3 center = mix(aScatter + drift, aStack, g);
  center.y += sin(g * 3.14159) * (aSeed - 0.5) * 1.4;
  vec3 p = rotXYZ(rot) * (position * scale);
  vec4 mv = modelViewMatrix * vec4(center + p, 1.);
  gl_Position = projectionMatrix * mv;
  vUv = uv;
  vKind = aKind;
  vSeed = aSeed;
  vG = g;
  vFade = smoothstep(-30., -9., mv.z) * smoothstep(-0.5, -3., mv.z);
}
`;

export const cardFragment = /* glsl */ `
uniform vec3 uInk;
uniform vec3 uMint;
uniform vec3 uCoral;
varying vec2 vUv;
varying float vKind;
varying float vSeed;
varying float vG;
varying float vFade;
varying float vDepth;

float sdBox(vec2 p, vec2 b, float r) {
  vec2 q = abs(p) - b + r;
  return length(max(q, 0.)) + min(max(q.x, q.y), 0.) - r;
}
float fill(float d) {
  float aa = fwidth(d);
  return 1. - smoothstep(-aa, aa, d);
}
float hash(float n) { return fract(sin(n) * 43758.5453); }

void main() {
  vec2 p = (vUv - .5) * vec2(1., 1.3);
  float d = sdBox(p, vec2(.5, .65), .07);
  float shape = fill(d);
  if (shape < .01) discard;

  vec3 col = mix(vec3(1.), uMint, .12 + .1 * (1. - vUv.y));
  float ink = 0.;
  vec3 inkCol = uInk;

  // title bar
  ink += fill(sdBox(p - vec2(-.16, .5), vec2(.24, .032), .032)) * .7;
  ink += fill(sdBox(p - vec2(.3, .5), vec2(.08, .032), .032)) * .25;

  if (vKind < .5) {
    // prescription: ruled lines of varying length
    float rowH = .085;
    float y = p.y + .42;
    float row = floor(y / rowH);
    float inRows = step(0., y) * step(y, .78);
    float len = .35 + .5 * hash(row + vSeed * 31.);
    float line = fill(sdBox(vec2(p.x + .38 - len * .38, mod(y, rowH) - rowH * .5), vec2(len * .38, .011), .011));
    ink += line * inRows * .32;
  } else if (vKind < 1.5) {
    // lab sheet: label column + value pills, one flagged row in coral
    float rowH = .1;
    float y = p.y + .42;
    float row = floor(y / rowH);
    float inRows = step(0., y) * step(y, .8);
    float ry = mod(y, rowH) - rowH * .5;
    ink += fill(sdBox(vec2(p.x + .2, ry), vec2(.18, .012), .012)) * inRows * .3;
    float val = fill(sdBox(vec2(p.x - .27, ry), vec2(.09, .022), .022)) * inRows;
    float flagged = step(.82, hash(row * 3.1 + vSeed * 17.));
    col = mix(col, mix(uMint, uCoral, flagged), val * .7);
  } else {
    // imaging: dark plate with a soft luminous structure
    float plate = fill(sdBox(p - vec2(0., -.05), vec2(.4, .45), .05));
    vec2 q = p - vec2(.02 * sin(vSeed * 20.), -.05);
    float body = exp(-dot(q * vec2(2.4, 1.6), q * vec2(2.4, 1.6)) * 3.);
    vec3 scan = mix(uInk * .9, mix(uMint, vec3(1.), .4), body * .85);
    col = mix(col, scan, plate);
  }
  col = mix(col, inkCol, clamp(ink, 0., 1.));

  // rim light: brighter once gathered into the record
  float rim = 1. - smoothstep(0., .03, abs(d));
  col = mix(col, mix(vec3(1.), uMint, .6), rim * (.35 + .5 * vG));

  // once stacked, only the front sheets read clearly: deeper ones fade so layers don't speckle
  float stackFade = mix(1., mix(.08, 1., vDepth * vDepth * vDepth), vG);
  float alpha = shape * mix(.62, .9, vG) * vFade * stackFade;
  gl_FragColor = vec4(col, alpha);
}
`;

export const particleVertex = /* glsl */ `
uniform float uTime;
uniform float uAssemble;
uniform float uPixelRatio;
attribute vec3 aLogo;
attribute float aSeed;
varying float vAlpha;
varying float vA;
void main() {
  vec3 field = position + vec3(sin(uTime * .09 + aSeed * 20.) * .35, cos(uTime * .11 + aSeed * 13.) * .3, sin(uTime * .07 + aSeed * 5.) * .3);
  float a = smoothstep(aSeed * .35, aSeed * .35 + .65, uAssemble);
  a = a * a * (3. - 2. * a);
  vec3 p = mix(field, aLogo, a);
  vec4 mv = modelViewMatrix * vec4(p, 1.);
  gl_Position = projectionMatrix * mv;
  gl_PointSize = (1.6 + aSeed * 1.8) * uPixelRatio * (11. / -mv.z);
  vAlpha = mix(.25 + .45 * aSeed, .95, a);
  vA = a;
}
`;

export const particleFragment = /* glsl */ `
uniform vec3 uMint;
uniform vec3 uInk;
varying float vAlpha;
varying float vA;
void main() {
  vec2 c = gl_PointCoord - .5;
  float d = length(c);
  float disc = 1. - smoothstep(.3, .5, d);
  if (disc < .01) discard;
  gl_FragColor = vec4(mix(uMint, uInk, vA * .85), disc * vAlpha);
}
`;

export const threadVertex = /* glsl */ `
attribute float aIndex;
varying float vT;
varying float vIndex;
void main() {
  vT = uv.x;
  vIndex = aIndex;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.);
}
`;

export const threadFragment = /* glsl */ `
uniform float uTime;
uniform float uReveal;
uniform float uFocus;
uniform float uFocusIndex;
uniform vec3 uLine;
uniform vec3 uStrong;
varying float vT;
varying float vIndex;
void main() {
  float reveal = clamp(uReveal * 1.35 - vIndex * .06, 0., 1.);
  float drawn = 1. - smoothstep(reveal - .04, reveal, vT);
  float isFocus = 1. - step(.5, abs(vIndex - uFocusIndex));
  float level = mix(.55, mix(.1, 1., isFocus), uFocus);
  float pulsePos = fract(uTime * .28 + vIndex * .19);
  float pulse = smoothstep(.09, 0., abs(pulsePos - vT)) * mix(.7, isFocus, uFocus);
  vec3 col = mix(uLine, uStrong, isFocus * uFocus + pulse * .5);
  gl_FragColor = vec4(col, drawn * clamp(level + pulse * .6, 0., 1.));
}
`;

export const nodeVertex = /* glsl */ `
uniform float uPixelRatio;
uniform float uReveal;
uniform float uFocus;
uniform float uFocusIndex;
uniform float uTime;
attribute float aIndex;
varying float vFocus;
varying float vVisible;
void main() {
  float isFocus = 1. - step(.5, abs(aIndex - uFocusIndex));
  vFocus = isFocus * uFocus;
  float appear = smoothstep(.55 + aIndex * .06, .8 + aIndex * .06, uReveal * 1.35);
  vVisible = appear * mix(1., mix(.3, 1., isFocus), uFocus);
  vec4 mv = modelViewMatrix * vec4(position, 1.);
  gl_Position = projectionMatrix * mv;
  float breathe = 1. + .05 * sin(uTime * 1.2 + aIndex);
  gl_PointSize = (34. + 16. * vFocus) * breathe * uPixelRatio * (10. / -mv.z) * appear;
}
`;

export const nodeFragment = /* glsl */ `
uniform vec3 uMint;
uniform vec3 uStrong;
varying float vFocus;
varying float vVisible;
void main() {
  float d = length(gl_PointCoord - .5);
  float core = 1. - smoothstep(.16, .2, d);
  float halo = (1. - smoothstep(.2, .5, d)) * .35;
  float ring = (1. - smoothstep(.0, .025, abs(d - .3))) * vFocus;
  float a = (core + halo + ring * .8) * vVisible;
  if (a < .01) discard;
  vec3 col = mix(uMint, uStrong, core * (.6 + .4 * vFocus));
  gl_FragColor = vec4(col, a);
}
`;

export const glowVertex = /* glsl */ `
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.);
}
`;

export const glowFragment = /* glsl */ `
uniform vec3 uMint;
uniform float uGlow;
varying vec2 vUv;
void main() {
  float d = length(vUv - .5);
  float a = exp(-d * d * 14.) * .75 * uGlow;
  gl_FragColor = vec4(uMint, a);
}
`;
