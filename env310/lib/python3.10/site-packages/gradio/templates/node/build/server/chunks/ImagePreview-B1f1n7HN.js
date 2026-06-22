import { f as fallback } from './async-D55cHugf.js';
import { f as attr_class, d as bind_props } from './index-6p4UEISu.js';
import { P as Ps } from './2-Dui6HgsZ.js';
import { k } from './BlockLabel-Cwr2q1Ma.js';
import { u } from './DownloadLink-eCzvV1uC.js';
import { w } from './IconButton-DoTLxBZ_.js';
import { p } from './Empty-cEfRNAPl.js';
import { y as y$1 } from './ShareButton-CXMjDbEI.js';
import { l } from './Download-DcU5dONL.js';
import { i } from './Image2-vcp9_ifi.js';
import { y } from './IconButtonWrapper-DtthXzCF.js';
import { v } from './FullscreenButton-C1W4Pgtf.js';
import { $ } from './Image-BLUJV7QV.js';
import './escaping-CBnpiEl5.js';
import './context-CBkBucIx.js';
import './index5-BoOEKc6P.js';
import './dev-fallback-Bc5Ork7Y.js';
import './index-Cg-Pg6j3.js';
import './index-server-CQz6EZl_.js';
import './Maximize-CuHbK64j.js';

/* empty css                                          */function O(g,o){g.component(a=>{let u$1=o.value,n=fallback(o.label,void 0),m=o.show_label,i$1=fallback(o.buttons,()=>[],true),f=fallback(o.on_custom_button_click,null),p$1=fallback(o.selectable,false),c=o.i18n,b=fallback(o.display_icon_button_wrapper_top_corner,false),e=fallback(o.fullscreen,false),h=fallback(o.show_button_background,true);k(a,{show_label:m,Icon:i,label:m?n||c("image.image"):""}),a.push("<!----> "),u$1==null||!u$1?.url?(a.push("<!--[-->"),p(a,{unpadded_box:true,size:"large",children:t=>{i(t);},$$slots:{default:true}})):(a.push("<!--[!-->"),a.push('<div class="image-container svelte-12vrxzd">'),y(a,{display_top_corner:b,show_background:h,buttons:i$1,on_custom_button_click:f,children:t=>{i$1.some(l=>typeof l=="string"&&l==="fullscreen")?(t.push("<!--[-->"),v(t,{fullscreen:e,onclick:l=>{e=l;}})):t.push("<!--[!-->"),t.push("<!--]--> "),i$1.some(l=>typeof l=="string"&&l==="download")?(t.push("<!--[-->"),u(t,{href:u$1.url,download:u$1.orig_name||"image",children:l$1=>{w(l$1,{Icon:l,label:c("common.download")});},$$slots:{default:true}})):t.push("<!--[!-->"),t.push("<!--]--> "),i$1.some(l=>typeof l=="string"&&l==="share")?(t.push("<!--[-->"),y$1(t,{i18n:c,formatter:async l=>l?`<img src="${await Ps(l)}" />`:"",value:u$1})):t.push("<!--[!-->"),t.push("<!--]-->");}}),a.push(`<!----> <button class="svelte-12vrxzd"><div${attr_class("image-frame svelte-12vrxzd",void 0,{selectable:p$1})}>`),$(a,{src:u$1.url,restProps:{loading:"lazy",alt:""}}),a.push("<!----></div></button></div>")),a.push("<!--]-->"),bind_props(o,{value:u$1,label:n,show_label:m,buttons:i$1,on_custom_button_click:f,selectable:p$1,i18n:c,display_icon_button_wrapper_top_corner:b,fullscreen:e,show_button_background:h});});}

export { O as default };
//# sourceMappingURL=ImagePreview-B1f1n7HN.js.map
