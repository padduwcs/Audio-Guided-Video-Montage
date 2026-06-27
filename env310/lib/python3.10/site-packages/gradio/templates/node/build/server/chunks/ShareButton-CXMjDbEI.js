import { f as fallback } from './async-D55cHugf.js';
import { d as bind_props } from './index-6p4UEISu.js';
import { w } from './IconButton-DoTLxBZ_.js';
import { c as createEventDispatcher } from './index-server-CQz6EZl_.js';
import { X as Xe } from './2-Dui6HgsZ.js';

function p(o){o.push('<svg id="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="100%" height="100%"><path d="M23,20a5,5,0,0,0-3.89,1.89L11.8,17.32a4.46,4.46,0,0,0,0-2.64l7.31-4.57A5,5,0,1,0,18,7a4.79,4.79,0,0,0,.2,1.32l-7.31,4.57a5,5,0,1,0,0,6.22l7.31,4.57A4.79,4.79,0,0,0,18,25a5,5,0,1,0,5-5ZM23,4a3,3,0,1,1-3,3A3,3,0,0,1,23,4ZM7,19a3,3,0,1,1,3-3A3,3,0,0,1,7,19Zm16,9a3,3,0,1,1,3-3A3,3,0,0,1,23,28Z" fill="currentColor"></path></svg>');}function y(o,e){o.component(h=>{const i=createEventDispatcher();let l=e.formatter,s=e.value,c=e.i18n,m=fallback(e.onerror,void 0),f=fallback(e.onshare,void 0),r=false;w(h,{Icon:p,label:c("common.share"),pending:r,onclick:async()=>{try{r=!0;const t={description:await l(s)};i("share",t),f?.(t);}catch(a){console.error(a);let t=a instanceof Xe?a.message:"Share failed.";m?.(t);}finally{r=false;}}}),bind_props(e,{formatter:l,value:s,i18n:c,onerror:m,onshare:f});});}

export { p, y };
//# sourceMappingURL=ShareButton-CXMjDbEI.js.map
