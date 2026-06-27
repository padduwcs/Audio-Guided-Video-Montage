import{S as r}from"./index-BVk3QIoo.js";import"./index-CU1DelDP.js";const a="shadowMapFragmentSoftTransparentShadow",o=`#if SM_SOFTTRANSPARENTSHADOW==1
if ((bayerDither8(floor(mod(gl_FragCoord.xy,8.0))))/64.0>=softTransparentShadowSM.x*alpha) discard;
#endif
`;r.IncludesShadersStore[a]||(r.IncludesShadersStore[a]=o);const S={name:a,shader:o};export{S as shadowMapFragmentSoftTransparentShadow};
