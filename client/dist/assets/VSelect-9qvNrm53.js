import{l as wt,b as Vt,d as $e,n as Ct,o as It,c as Me}from"./VTextField-Cn4WKwf3.js";import{E as X,G as N,T as le,C as p,O as J,Y as ge,a as m,Q as $,X as Q,bp as ye,aj as K,ae as he,cE as Te,c4 as R,S as Ge,bC as qe,ad as xe,q as M,cX as ze,an as D,cY as ve,cZ as Pt,w as We,v as At,I as be,J as oe,R as Tt,c_ as xt,s as te,ah as Xe,c$ as Ye,d0 as Lt,cP as Qe,d1 as Le,cV as Je,cW as Ze,d2 as Ot,j as Bt,ao as et,ap as tt,d3 as Et,ar as nt,as as at,d4 as Oe,at as lt,au as it,d5 as de,d6 as Dt,F as ie,d7 as ke,cK as Mt,d8 as Rt,d9 as ee,cQ as Ft,ak as _t,da as Se,ag as jt,bD as Ht,a3 as Be,db as Re,dc as Nt,dd as fe,de as Ut,al as ot,ai as Kt,cp as Fe,df as $t,bH as ut,cI as Ve,cR as Gt,dg as qt,x as zt,cH as pe,af as Wt,dh as _e,di as je,dj as Xt,l as Yt}from"./index-B7OgWKtM.js";import{M as Qt,V as Ie,m as Jt}from"./VAvatar-CxE9IZav.js";import{V as He,m as Zt,f as en,d as Ne,i as tn,j as st,k as Ue,l as nn,c as an}from"./VChip-CXvR9eN_.js";import{u as ln,c as on}from"./ssrBoot-CgU2lsL7.js";const un=N({indeterminate:Boolean,indeterminateIcon:{type:Q,default:"$checkboxIndeterminate"},...Zt({falseIcon:"$checkboxOff",trueIcon:"$checkboxOn"})},"VCheckboxBtn"),sn=X()({name:"VCheckboxBtn",props:un(),emits:{"update:modelValue":e=>!0,"update:indeterminate":e=>!0},setup(e,i){let{slots:t}=i;const n=le(e,"indeterminate"),l=le(e,"modelValue");function a(c){n.value&&(n.value=!1)}const o=p(()=>n.value?e.indeterminateIcon:e.falseIcon),u=p(()=>n.value?e.indeterminateIcon:e.trueIcon);return J(()=>{const c=ge(He.filterProps(e),["modelValue"]);return m(He,$(c,{modelValue:l.value,"onUpdate:modelValue":[v=>l.value=v,a],class:["v-checkbox-btn",e.class],style:e.style,type:"checkbox",falseIcon:o.value,trueIcon:u.value,"aria-checked":n.value?"mixed":void 0}),t)}),{}}}),Pe=Symbol.for("vuetify:list");function rt(){const e=ye(Pe,{hasPrepend:K(!1),updateHasPrepend:()=>null}),i={hasPrepend:K(!1),updateHasPrepend:t=>{t&&(i.hasPrepend.value=t)}};return he(Pe,i),e}function ct(){return ye(Pe,null)}const Ee=e=>{const i={activate:t=>{let{id:n,value:l,activated:a}=t;return n=R(n),e&&!l&&a.size===1&&a.has(n)||(l?a.add(n):a.delete(n)),a},in:(t,n,l)=>{let a=new Set;if(t!=null)for(const o of Te(t))a=i.activate({id:o,value:!0,activated:new Set(a),children:n,parents:l});return a},out:t=>Array.from(t)};return i},dt=e=>{const i=Ee(e);return{activate:n=>{let{activated:l,id:a,...o}=n;a=R(a);const u=l.has(a)?new Set([a]):new Set;return i.activate({...o,id:a,activated:u})},in:(n,l,a)=>{let o=new Set;if(n!=null){const u=Te(n);u.length&&(o=i.in(u.slice(0,1),l,a))}return o},out:(n,l,a)=>i.out(n,l,a)}},rn=e=>{const i=Ee(e);return{activate:n=>{let{id:l,activated:a,children:o,...u}=n;return l=R(l),o.has(l)?a:i.activate({id:l,activated:a,children:o,...u})},in:i.in,out:i.out}},cn=e=>{const i=dt(e);return{activate:n=>{let{id:l,activated:a,children:o,...u}=n;return l=R(l),o.has(l)?a:i.activate({id:l,activated:a,children:o,...u})},in:i.in,out:i.out}},dn={open:e=>{let{id:i,value:t,opened:n,parents:l}=e;if(t){const a=new Set;a.add(i);let o=l.get(i);for(;o!=null;)a.add(o),o=l.get(o);return a}else return n.delete(i),n},select:()=>null},vt={open:e=>{let{id:i,value:t,opened:n,parents:l}=e;if(t){let a=l.get(i);for(n.add(i);a!=null&&a!==i;)n.add(a),a=l.get(a);return n}else n.delete(i);return n},select:()=>null},vn={open:vt.open,select:e=>{let{id:i,value:t,opened:n,parents:l}=e;if(!t)return n;const a=[];let o=l.get(i);for(;o!=null;)a.push(o),o=l.get(o);return new Set(a)}},De=e=>{const i={select:t=>{let{id:n,value:l,selected:a}=t;if(n=R(n),e&&!l){const o=Array.from(a.entries()).reduce((u,c)=>{let[v,V]=c;return V==="on"&&u.push(v),u},[]);if(o.length===1&&o[0]===n)return a}return a.set(n,l?"on":"off"),a},in:(t,n,l)=>{let a=new Map;for(const o of t||[])a=i.select({id:o,value:!0,selected:new Map(a),children:n,parents:l});return a},out:t=>{const n=[];for(const[l,a]of t.entries())a==="on"&&n.push(l);return n}};return i},ft=e=>{const i=De(e);return{select:n=>{let{selected:l,id:a,...o}=n;a=R(a);const u=l.has(a)?new Map([[a,l.get(a)]]):new Map;return i.select({...o,id:a,selected:u})},in:(n,l,a)=>{let o=new Map;return n!=null&&n.length&&(o=i.in(n.slice(0,1),l,a)),o},out:(n,l,a)=>i.out(n,l,a)}},fn=e=>{const i=De(e);return{select:n=>{let{id:l,selected:a,children:o,...u}=n;return l=R(l),o.has(l)?a:i.select({id:l,selected:a,children:o,...u})},in:i.in,out:i.out}},mn=e=>{const i=ft(e);return{select:n=>{let{id:l,selected:a,children:o,...u}=n;return l=R(l),o.has(l)?a:i.select({id:l,selected:a,children:o,...u})},in:i.in,out:i.out}},gn=e=>{const i={select:t=>{let{id:n,value:l,selected:a,children:o,parents:u}=t;n=R(n);const c=new Map(a),v=[n];for(;v.length;){const C=v.shift();a.set(R(C),l?"on":"off"),o.has(C)&&v.push(...o.get(C))}let V=R(u.get(n));for(;V;){const C=o.get(V),b=C.every(r=>a.get(R(r))==="on"),k=C.every(r=>!a.has(R(r))||a.get(R(r))==="off");a.set(V,b?"on":k?"off":"indeterminate"),V=R(u.get(V))}return e&&!l&&Array.from(a.entries()).reduce((b,k)=>{let[r,f]=k;return f==="on"&&b.push(r),b},[]).length===0?c:a},in:(t,n,l)=>{let a=new Map;for(const o of t||[])a=i.select({id:o,value:!0,selected:new Map(a),children:n,parents:l});return a},out:(t,n)=>{const l=[];for(const[a,o]of t.entries())o==="on"&&!n.has(a)&&l.push(a);return l}};return i},me=Symbol.for("vuetify:nested"),mt={id:K(),root:{register:()=>null,unregister:()=>null,parents:M(new Map),children:M(new Map),open:()=>null,openOnSelect:()=>null,activate:()=>null,select:()=>null,activatable:M(!1),selectable:M(!1),opened:M(new Set),activated:M(new Set),selected:M(new Map),selectedValues:M([]),getPath:()=>[]}},yn=N({activatable:Boolean,selectable:Boolean,activeStrategy:[String,Function,Object],selectStrategy:[String,Function,Object],openStrategy:[String,Object],opened:null,activated:null,selected:null,mandatory:Boolean},"nested"),hn=e=>{let i=!1;const t=M(new Map),n=M(new Map),l=le(e,"opened",e.opened,r=>new Set(r),r=>[...r.values()]),a=p(()=>{if(typeof e.activeStrategy=="object")return e.activeStrategy;if(typeof e.activeStrategy=="function")return e.activeStrategy(e.mandatory);switch(e.activeStrategy){case"leaf":return rn(e.mandatory);case"single-leaf":return cn(e.mandatory);case"independent":return Ee(e.mandatory);case"single-independent":default:return dt(e.mandatory)}}),o=p(()=>{if(typeof e.selectStrategy=="object")return e.selectStrategy;if(typeof e.selectStrategy=="function")return e.selectStrategy(e.mandatory);switch(e.selectStrategy){case"single-leaf":return mn(e.mandatory);case"leaf":return fn(e.mandatory);case"independent":return De(e.mandatory);case"single-independent":return ft(e.mandatory);case"classic":default:return gn(e.mandatory)}}),u=p(()=>{if(typeof e.openStrategy=="object")return e.openStrategy;switch(e.openStrategy){case"list":return vn;case"single":return dn;case"multiple":default:return vt}}),c=le(e,"activated",e.activated,r=>a.value.in(r,t.value,n.value),r=>a.value.out(r,t.value,n.value)),v=le(e,"selected",e.selected,r=>o.value.in(r,t.value,n.value),r=>o.value.out(r,t.value,n.value));xe(()=>{i=!0});function V(r){const f=[];let s=r;for(;s!=null;)f.unshift(s),s=n.value.get(s);return f}const C=ze("nested"),b=new Set,k={id:K(),root:{opened:l,activatable:D(e,"activatable"),selectable:D(e,"selectable"),activated:c,selected:v,selectedValues:p(()=>{const r=[];for(const[f,s]of v.value.entries())s==="on"&&r.push(f);return r}),register:(r,f,s)=>{if(b.has(r)){V(r).map(String).join(" -> "),V(f).concat(r).map(String).join(" -> ");return}else b.add(r);f&&r!==f&&n.value.set(r,f),s&&t.value.set(r,[]),f!=null&&t.value.set(f,[...t.value.get(f)||[],r])},unregister:r=>{if(i)return;b.delete(r),t.value.delete(r);const f=n.value.get(r);if(f){const s=t.value.get(f)??[];t.value.set(f,s.filter(h=>h!==r))}n.value.delete(r)},open:(r,f,s)=>{C.emit("click:open",{id:r,value:f,path:V(r),event:s});const h=u.value.open({id:r,value:f,opened:new Set(l.value),children:t.value,parents:n.value,event:s});h&&(l.value=h)},openOnSelect:(r,f,s)=>{const h=u.value.select({id:r,value:f,selected:new Map(v.value),opened:new Set(l.value),children:t.value,parents:n.value,event:s});h&&(l.value=h)},select:(r,f,s)=>{C.emit("click:select",{id:r,value:f,path:V(r),event:s});const h=o.value.select({id:r,value:f,selected:new Map(v.value),children:t.value,parents:n.value,event:s});h&&(v.value=h),k.root.openOnSelect(r,f,s)},activate:(r,f,s)=>{if(!e.activatable)return k.root.select(r,!0,s);C.emit("click:activate",{id:r,value:f,path:V(r),event:s});const h=a.value.activate({id:r,value:f,activated:new Set(c.value),children:t.value,parents:n.value,event:s});h&&(c.value=h)},children:t,parents:n,getPath:V}};return he(me,k),k.root},gt=(e,i)=>{const t=ye(me,mt),n=Symbol(Ge()),l=p(()=>e.value!==void 0?e.value:n),a={...t,id:l,open:(o,u)=>t.root.open(l.value,o,u),openOnSelect:(o,u)=>t.root.openOnSelect(l.value,o,u),isOpen:p(()=>t.root.opened.value.has(l.value)),parent:p(()=>t.root.parents.value.get(l.value)),activate:(o,u)=>t.root.activate(l.value,o,u),isActivated:p(()=>t.root.activated.value.has(R(l.value))),select:(o,u)=>t.root.select(l.value,o,u),isSelected:p(()=>t.root.selected.value.get(R(l.value))==="on"),isIndeterminate:p(()=>t.root.selected.value.get(R(l.value))==="indeterminate"),isLeaf:p(()=>!t.root.children.value.get(l.value)),isGroupActivator:t.isGroupActivator};return qe(()=>{!t.isGroupActivator&&t.root.register(l.value,t.id.value,i)}),xe(()=>{!t.isGroupActivator&&t.root.unregister(l.value)}),i&&he(me,a),a},bn=()=>{const e=ye(me,mt);he(me,{...e,isGroupActivator:!0})},pn=Pt({name:"VListGroupActivator",setup(e,i){let{slots:t}=i;return bn(),()=>{var n;return(n=t.default)==null?void 0:n.call(t)}}}),Sn=N({activeColor:String,baseColor:String,color:String,collapseIcon:{type:Q,default:"$collapse"},expandIcon:{type:Q,default:"$expand"},prependIcon:Q,appendIcon:Q,fluid:Boolean,subgroup:Boolean,title:String,value:null,...oe(),...be()},"VListGroup"),Ke=X()({name:"VListGroup",props:Sn(),setup(e,i){let{slots:t}=i;const{isOpen:n,open:l,id:a}=gt(D(e,"value"),!0),o=p(()=>`v-list-group--id-${String(a.value)}`),u=ct(),{isBooted:c}=ln();function v(k){k.stopPropagation(),l(!n.value,k)}const V=p(()=>({onClick:v,class:"v-list-group__header",id:o.value})),C=p(()=>n.value?e.collapseIcon:e.expandIcon),b=p(()=>({VListItem:{active:n.value,activeColor:e.activeColor,baseColor:e.baseColor,color:e.color,prependIcon:e.prependIcon||e.subgroup&&C.value,appendIcon:e.appendIcon||!e.subgroup&&C.value,title:e.title,value:e.value}}));return J(()=>m(e.tag,{class:["v-list-group",{"v-list-group--prepend":u==null?void 0:u.hasPrepend.value,"v-list-group--fluid":e.fluid,"v-list-group--subgroup":e.subgroup,"v-list-group--open":n.value},e.class],style:e.style},{default:()=>[t.activator&&m(ve,{defaults:b.value},{default:()=>[m(pn,null,{default:()=>[t.activator({props:V.value,isOpen:n.value})]})]}),m(Qt,{transition:{component:wt},disabled:!c.value},{default:()=>{var k;return[We(m("div",{class:"v-list-group__items",role:"group","aria-labelledby":o.value},[(k=t.default)==null?void 0:k.call(t)]),[[At,n.value]])]}})]})),{isOpen:n}}}),kn=N({opacity:[Number,String],...oe(),...be()},"VListItemSubtitle"),wn=X()({name:"VListItemSubtitle",props:kn(),setup(e,i){let{slots:t}=i;return J(()=>m(e.tag,{class:["v-list-item-subtitle",e.class],style:[{"--v-list-item-subtitle-opacity":e.opacity},e.style]},t)),{}}}),Vn=on("v-list-item-title"),Cn=N({active:{type:Boolean,default:void 0},activeClass:String,activeColor:String,appendAvatar:String,appendIcon:Q,baseColor:String,disabled:Boolean,lines:[Boolean,String],link:{type:Boolean,default:void 0},nav:Boolean,prependAvatar:String,prependIcon:Q,ripple:{type:[Boolean,Object],default:!0},slim:Boolean,subtitle:[String,Number],title:[String,Number],value:null,onClick:de(),onClickOnce:de(),...it(),...oe(),...lt(),...Oe(),...at(),...nt(),...Et(),...be(),...tt(),...et({variant:"text"})},"VListItem"),we=X()({name:"VListItem",directives:{Ripple:Tt},props:Cn(),emits:{click:e=>!0},setup(e,i){let{attrs:t,slots:n,emit:l}=i;const a=xt(e,t),o=p(()=>e.value===void 0?a.href.value:e.value),{activate:u,isActivated:c,select:v,isOpen:V,isSelected:C,isIndeterminate:b,isGroupActivator:k,root:r,parent:f,openOnSelect:s,id:h}=gt(o,!1),w=ct(),I=p(()=>{var y;return e.active!==!1&&(e.active||((y=a.isActive)==null?void 0:y.value)||(r.activatable.value?c.value:C.value))}),P=p(()=>e.link!==!1&&a.isLink.value),B=p(()=>!!w&&(r.selectable.value||r.activatable.value||e.value!=null)),E=p(()=>!e.disabled&&e.link!==!1&&(e.link||a.isClickable.value||B.value)),O=p(()=>e.rounded||e.nav),ne=p(()=>e.color??e.activeColor),Y=p(()=>({color:I.value?ne.value??e.baseColor:e.baseColor,variant:e.variant}));te(()=>{var y;return(y=a.isActive)==null?void 0:y.value},y=>{y&&G()}),qe(()=>{var y;(y=a.isActive)!=null&&y.value&&G()});function G(){f.value!=null&&r.open(f.value,!0),s(!0)}const{themeClasses:Z}=Xe(e),{borderClasses:j}=Ye(e),{colorClasses:T,colorStyles:z,variantClasses:ue}=Lt(Y),{densityClasses:W}=Qe(e),{dimensionStyles:re}=Le(e),{elevationClasses:se}=Je(e),{roundedClasses:g}=Ze(O),d=p(()=>e.lines?`v-list-item--${e.lines}-line`:void 0),S=p(()=>({isActive:I.value,select:v,isOpen:V.value,isSelected:C.value,isIndeterminate:b.value}));function x(y){var A;l("click",y),E.value&&((A=a.navigate)==null||A.call(a,y),!k&&(r.activatable.value?u(!c.value,y):(r.selectable.value||e.value!=null)&&v(!C.value,y)))}function L(y){(y.key==="Enter"||y.key===" ")&&(y.preventDefault(),y.target.dispatchEvent(new MouseEvent("click",y)))}return J(()=>{const y=P.value?"a":e.tag,A=n.title||e.title!=null,F=n.subtitle||e.subtitle!=null,q=!!(e.appendAvatar||e.appendIcon),H=!!(q||n.append),ae=!!(e.prependAvatar||e.prependIcon),_=!!(ae||n.prepend);return w==null||w.updateHasPrepend(_),e.activeColor&&Ot("active-color",["color","base-color"]),We(m(y,$({class:["v-list-item",{"v-list-item--active":I.value,"v-list-item--disabled":e.disabled,"v-list-item--link":E.value,"v-list-item--nav":e.nav,"v-list-item--prepend":!_&&(w==null?void 0:w.hasPrepend.value),"v-list-item--slim":e.slim,[`${e.activeClass}`]:e.activeClass&&I.value},Z.value,j.value,T.value,W.value,se.value,d.value,g.value,ue.value,e.class],style:[z.value,re.value,e.style],tabindex:E.value?w?-2:0:void 0,"aria-selected":B.value?r.activatable.value?c.value:r.selectable.value?C.value:I.value:void 0,onClick:x,onKeydown:E.value&&!P.value&&L},a.linkProps),{default:()=>{var ce;return[Dt(E.value||I.value,"v-list-item"),_&&m("div",{key:"prepend",class:"v-list-item__prepend"},[n.prepend?m(ve,{key:"prepend-defaults",disabled:!ae,defaults:{VAvatar:{density:e.density,image:e.prependAvatar},VIcon:{density:e.density,icon:e.prependIcon},VListItemAction:{start:!0}}},{default:()=>{var U;return[(U=n.prepend)==null?void 0:U.call(n,S.value)]}}):m(ie,null,[e.prependAvatar&&m(Ie,{key:"prepend-avatar",density:e.density,image:e.prependAvatar},null),e.prependIcon&&m(ke,{key:"prepend-icon",density:e.density,icon:e.prependIcon},null)]),m("div",{class:"v-list-item__spacer"},null)]),m("div",{class:"v-list-item__content","data-no-activator":""},[A&&m(Vn,{key:"title"},{default:()=>{var U;return[((U=n.title)==null?void 0:U.call(n,{title:e.title}))??e.title]}}),F&&m(wn,{key:"subtitle"},{default:()=>{var U;return[((U=n.subtitle)==null?void 0:U.call(n,{subtitle:e.subtitle}))??e.subtitle]}}),(ce=n.default)==null?void 0:ce.call(n,S.value)]),H&&m("div",{key:"append",class:"v-list-item__append"},[n.append?m(ve,{key:"append-defaults",disabled:!q,defaults:{VAvatar:{density:e.density,image:e.appendAvatar},VIcon:{density:e.density,icon:e.appendIcon},VListItemAction:{end:!0}}},{default:()=>{var U;return[(U=n.append)==null?void 0:U.call(n,S.value)]}}):m(ie,null,[e.appendIcon&&m(ke,{key:"append-icon",density:e.density,icon:e.appendIcon},null),e.appendAvatar&&m(Ie,{key:"append-avatar",density:e.density,image:e.appendAvatar},null)]),m("div",{class:"v-list-item__spacer"},null)])]}}),[[Bt("ripple"),E.value&&e.ripple]])}),{activate:u,isActivated:c,isGroupActivator:k,isSelected:C,list:w,select:v,root:r,id:h}}}),In=N({color:String,inset:Boolean,sticky:Boolean,title:String,...oe(),...be()},"VListSubheader"),Pn=X()({name:"VListSubheader",props:In(),setup(e,i){let{slots:t}=i;const{textColorClasses:n,textColorStyles:l}=Mt(D(e,"color"));return J(()=>{const a=!!(t.default||e.title);return m(e.tag,{class:["v-list-subheader",{"v-list-subheader--inset":e.inset,"v-list-subheader--sticky":e.sticky},n.value,e.class],style:[{textColorStyles:l},e.style]},{default:()=>{var o;return[a&&m("div",{class:"v-list-subheader__text"},[((o=t.default)==null?void 0:o.call(t))??e.title])]}})}),{}}}),An=N({items:Array,returnObject:Boolean},"VListChildren"),yt=X()({name:"VListChildren",props:An(),setup(e,i){let{slots:t}=i;return rt(),()=>{var n,l;return((n=t.default)==null?void 0:n.call(t))??((l=e.items)==null?void 0:l.map(a=>{var b,k;let{children:o,props:u,type:c,raw:v}=a;if(c==="divider")return((b=t.divider)==null?void 0:b.call(t,{props:u}))??m(Vt,u,null);if(c==="subheader")return((k=t.subheader)==null?void 0:k.call(t,{props:u}))??m(Pn,u,null);const V={subtitle:t.subtitle?r=>{var f;return(f=t.subtitle)==null?void 0:f.call(t,{...r,item:v})}:void 0,prepend:t.prepend?r=>{var f;return(f=t.prepend)==null?void 0:f.call(t,{...r,item:v})}:void 0,append:t.append?r=>{var f;return(f=t.append)==null?void 0:f.call(t,{...r,item:v})}:void 0,title:t.title?r=>{var f;return(f=t.title)==null?void 0:f.call(t,{...r,item:v})}:void 0},C=Ke.filterProps(u);return o?m(Ke,$({value:u==null?void 0:u.value},C),{activator:r=>{let{props:f}=r;const s={...u,...f,value:e.returnObject?v:u.value};return t.header?t.header({props:s}):m(we,s,V)},default:()=>m(yt,{items:o,returnObject:e.returnObject},t)}):t.item?t.item({props:u}):m(we,$(u,{value:e.returnObject?v:u.value}),V)}))}}}),ht=N({items:{type:Array,default:()=>[]},itemTitle:{type:[String,Array,Function],default:"title"},itemValue:{type:[String,Array,Function],default:"value"},itemChildren:{type:[Boolean,String,Array,Function],default:"children"},itemProps:{type:[Boolean,String,Array,Function],default:"props"},returnObject:Boolean,valueComparator:{type:Function,default:Rt}},"list-items");function Ae(e,i){const t=ee(i,e.itemTitle,i),n=ee(i,e.itemValue,t),l=ee(i,e.itemChildren),a=e.itemProps===!0?typeof i=="object"&&i!=null&&!Array.isArray(i)?"children"in i?ge(i,["children"]):i:void 0:ee(i,e.itemProps),o={title:t,value:n,...a};return{title:String(o.title??""),value:o.value,props:o,children:Array.isArray(l)?bt(e,l):void 0,raw:i}}function bt(e,i){const t=[];for(const n of i)t.push(Ae(e,n));return t}function Tn(e){const i=p(()=>bt(e,e.items)),t=p(()=>i.value.some(a=>a.value===null));function n(a){return t.value||(a=a.filter(o=>o!==null)),a.map(o=>e.returnObject&&typeof o=="string"?Ae(e,o):i.value.find(u=>e.valueComparator(o,u.value))||Ae(e,o))}function l(a){return e.returnObject?a.map(o=>{let{raw:u}=o;return u}):a.map(o=>{let{value:u}=o;return u})}return{items:i,transformIn:n,transformOut:l}}function xn(e){return typeof e=="string"||typeof e=="number"||typeof e=="boolean"}function Ln(e,i){const t=ee(i,e.itemType,"item"),n=xn(i)?i:ee(i,e.itemTitle),l=ee(i,e.itemValue,void 0),a=ee(i,e.itemChildren),o=e.itemProps===!0?ge(i,["children"]):ee(i,e.itemProps),u={title:n,value:l,...o};return{type:t,title:u.title,value:u.value,props:u,children:t==="item"&&a?pt(e,a):void 0,raw:i}}function pt(e,i){const t=[];for(const n of i)t.push(Ln(e,n));return t}function On(e){return{items:p(()=>pt(e,e.items))}}const Bn=N({baseColor:String,activeColor:String,activeClass:String,bgColor:String,disabled:Boolean,expandIcon:Q,collapseIcon:Q,lines:{type:[Boolean,String],default:"one"},slim:Boolean,nav:Boolean,"onClick:open":de(),"onClick:select":de(),"onUpdate:opened":de(),...yn({selectStrategy:"single-leaf",openStrategy:"list"}),...it(),...oe(),...lt(),...Oe(),...at(),itemType:{type:String,default:"type"},...ht(),...nt(),...be(),...tt(),...et({variant:"text"})},"VList"),En=X()({name:"VList",props:Bn(),emits:{"update:selected":e=>!0,"update:activated":e=>!0,"update:opened":e=>!0,"click:open":e=>!0,"click:activate":e=>!0,"click:select":e=>!0},setup(e,i){let{slots:t}=i;const{items:n}=On(e),{themeClasses:l}=Xe(e),{backgroundColorClasses:a,backgroundColorStyles:o}=Ft(D(e,"bgColor")),{borderClasses:u}=Ye(e),{densityClasses:c}=Qe(e),{dimensionStyles:v}=Le(e),{elevationClasses:V}=Je(e),{roundedClasses:C}=Ze(e),{children:b,open:k,parents:r,select:f,getPath:s}=hn(e),h=p(()=>e.lines?`v-list--${e.lines}-line`:void 0),w=D(e,"activeColor"),I=D(e,"baseColor"),P=D(e,"color");rt(),_t({VListGroup:{activeColor:w,baseColor:I,color:P,expandIcon:D(e,"expandIcon"),collapseIcon:D(e,"collapseIcon")},VListItem:{activeClass:D(e,"activeClass"),activeColor:w,baseColor:I,color:P,density:D(e,"density"),disabled:D(e,"disabled"),lines:D(e,"lines"),nav:D(e,"nav"),slim:D(e,"slim"),variant:D(e,"variant")}});const B=K(!1),E=M();function O(T){B.value=!0}function ne(T){B.value=!1}function Y(T){var z;!B.value&&!(T.relatedTarget&&((z=E.value)!=null&&z.contains(T.relatedTarget)))&&j()}function G(T){const z=T.target;if(!(!E.value||["INPUT","TEXTAREA"].includes(z.tagName))){if(T.key==="ArrowDown")j("next");else if(T.key==="ArrowUp")j("prev");else if(T.key==="Home")j("first");else if(T.key==="End")j("last");else return;T.preventDefault()}}function Z(T){B.value=!0}function j(T){if(E.value)return Se(E.value,T)}return J(()=>m(e.tag,{ref:E,class:["v-list",{"v-list--disabled":e.disabled,"v-list--nav":e.nav,"v-list--slim":e.slim},l.value,a.value,u.value,c.value,V.value,h.value,C.value,e.class],style:[o.value,v.value,e.style],tabindex:e.disabled||B.value?-1:0,role:"listbox","aria-activedescendant":void 0,onFocusin:O,onFocusout:ne,onFocus:Y,onKeydown:G,onMousedown:Z},{default:()=>[m(yt,{items:n.value,returnObject:e.returnObject},t)]})),{open:k,select:f,focus:j,children:b,parents:r,getPath:s}}}),Dn=N({id:String,submenu:Boolean,...ge(tn({closeDelay:250,closeOnContentClick:!0,locationStrategy:"connected",location:void 0,openDelay:300,scrim:!1,scrollStrategy:"reposition",transition:{component:st}}),["absolute"])},"VMenu"),Mn=X()({name:"VMenu",props:Dn(),emits:{"update:modelValue":e=>!0},setup(e,i){let{slots:t}=i;const n=le(e,"modelValue"),{scopeId:l}=en(),{isRtl:a}=jt(),o=Ge(),u=p(()=>e.id||`v-menu-${o}`),c=M(),v=ye(Ue,null),V=K(new Set);he(Ue,{register(){V.value.add(o)},unregister(){V.value.delete(o)},closeParents(s){setTimeout(()=>{var h;!V.value.size&&!e.persistent&&(s==null||(h=c.value)!=null&&h.contentEl&&!Ut(s,c.value.contentEl))&&(n.value=!1,v==null||v.closeParents())},40)}}),xe(()=>{v==null||v.unregister(),document.removeEventListener("focusin",C)}),Ht(()=>n.value=!1);async function C(s){var I,P,B;const h=s.relatedTarget,w=s.target;await Be(),n.value&&h!==w&&((I=c.value)!=null&&I.contentEl)&&((P=c.value)!=null&&P.globalTop)&&![document,c.value.contentEl].includes(w)&&!c.value.contentEl.contains(w)&&((B=Re(c.value.contentEl)[0])==null||B.focus())}te(n,s=>{s?(v==null||v.register(),fe&&document.addEventListener("focusin",C,{once:!0})):(v==null||v.unregister(),fe&&document.removeEventListener("focusin",C))},{immediate:!0});function b(s){v==null||v.closeParents(s)}function k(s){var h,w,I,P,B;if(!e.disabled)if(s.key==="Tab"||s.key==="Enter"&&!e.closeOnContentClick){if(s.key==="Enter"&&(s.target instanceof HTMLTextAreaElement||s.target instanceof HTMLInputElement&&s.target.closest("form")))return;s.key==="Enter"&&s.preventDefault(),Nt(Re((h=c.value)==null?void 0:h.contentEl,!1),s.shiftKey?"prev":"next",O=>O.tabIndex>=0)||(n.value=!1,(I=(w=c.value)==null?void 0:w.activatorEl)==null||I.focus())}else e.submenu&&s.key===(a.value?"ArrowRight":"ArrowLeft")&&(n.value=!1,(B=(P=c.value)==null?void 0:P.activatorEl)==null||B.focus())}function r(s){var w;if(e.disabled)return;const h=(w=c.value)==null?void 0:w.contentEl;h&&n.value?s.key==="ArrowDown"?(s.preventDefault(),s.stopImmediatePropagation(),Se(h,"next")):s.key==="ArrowUp"?(s.preventDefault(),s.stopImmediatePropagation(),Se(h,"prev")):e.submenu&&(s.key===(a.value?"ArrowRight":"ArrowLeft")?n.value=!1:s.key===(a.value?"ArrowLeft":"ArrowRight")&&(s.preventDefault(),Se(h,"first"))):(e.submenu?s.key===(a.value?"ArrowLeft":"ArrowRight"):["ArrowDown","ArrowUp"].includes(s.key))&&(n.value=!0,s.preventDefault(),setTimeout(()=>setTimeout(()=>r(s))))}const f=p(()=>$({"aria-haspopup":"menu","aria-expanded":String(n.value),"aria-controls":u.value,onKeydown:r},e.activatorProps));return J(()=>{const s=Ne.filterProps(e);return m(Ne,$({ref:c,id:u.value,class:["v-menu",e.class],style:e.style},s,{modelValue:n.value,"onUpdate:modelValue":h=>n.value=h,absolute:!0,activatorProps:f.value,location:e.location??(e.submenu?"end":"bottom"),"onClick:outside":b,onKeydown:k},l),{activator:t.activator,default:function(){for(var h=arguments.length,w=new Array(h),I=0;I<h;I++)w[I]=arguments[I];return m(ve,{root:"VMenu"},{default:()=>{var P;return[(P=t.default)==null?void 0:P.call(t,...w)]}})}})}),$e({id:u,ΨopenChildren:V},c)}}),Rn=N({renderless:Boolean,...oe()},"VVirtualScrollItem"),Fn=X()({name:"VVirtualScrollItem",inheritAttrs:!1,props:Rn(),emits:{"update:height":e=>!0},setup(e,i){let{attrs:t,emit:n,slots:l}=i;const{resizeRef:a,contentRect:o}=ot(void 0,"border");te(()=>{var u;return(u=o.value)==null?void 0:u.height},u=>{u!=null&&n("update:height",u)}),J(()=>{var u,c;return e.renderless?m(ie,null,[(u=l.default)==null?void 0:u.call(l,{itemRef:a})]):m("div",$({ref:a,class:["v-virtual-scroll__item",e.class],style:e.style},t),[(c=l.default)==null?void 0:c.call(l)])})}}),_n=-1,jn=1,Ce=100,Hn=N({itemHeight:{type:[Number,String],default:null},height:[Number,String]},"virtual");function Nn(e,i){const t=Kt(),n=K(0);Fe(()=>{n.value=parseFloat(e.itemHeight||0)});const l=K(0),a=K(Math.ceil((parseInt(e.height)||t.height.value)/(n.value||16))||1),o=K(0),u=K(0),c=M(),v=M();let V=0;const{resizeRef:C,contentRect:b}=ot();Fe(()=>{C.value=c.value});const k=p(()=>{var d;return c.value===document.documentElement?t.height.value:((d=b.value)==null?void 0:d.height)||parseInt(e.height)||0}),r=p(()=>!!(c.value&&v.value&&k.value&&n.value));let f=Array.from({length:i.value.length}),s=Array.from({length:i.value.length});const h=K(0);let w=-1;function I(d){return f[d]||n.value}const P=$t(()=>{const d=performance.now();s[0]=0;const S=i.value.length;for(let x=1;x<=S-1;x++)s[x]=(s[x-1]||0)+I(x-1);h.value=Math.max(h.value,performance.now()-d)},h),B=te(r,d=>{d&&(B(),V=v.value.offsetTop,P.immediate(),W(),~w&&Be(()=>{fe&&window.requestAnimationFrame(()=>{se(w),w=-1})}))});ut(()=>{P.clear()});function E(d,S){const x=f[d],L=n.value;n.value=L?Math.min(n.value,S):S,(x!==S||L!==n.value)&&(f[d]=S,P())}function O(d){return d=Ve(d,0,i.value.length-1),s[d]||0}function ne(d){return Un(s,d)}let Y=0,G=0,Z=0;te(k,(d,S)=>{S&&(W(),d<S&&requestAnimationFrame(()=>{G=0,W()}))});let j=-1;function T(){if(!c.value||!v.value)return;const d=c.value.scrollTop,S=performance.now();S-Z>500?(G=Math.sign(d-Y),V=v.value.offsetTop):G=d-Y,Y=d,Z=S,window.clearTimeout(j),j=window.setTimeout(z,500),W()}function z(){!c.value||!v.value||(G=0,Z=0,window.clearTimeout(j),W())}let ue=-1;function W(){cancelAnimationFrame(ue),ue=requestAnimationFrame(re)}function re(){if(!c.value||!k.value)return;const d=Y-V,S=Math.sign(G),x=Math.max(0,d-Ce),L=Ve(ne(x),0,i.value.length),y=d+k.value+Ce,A=Ve(ne(y)+1,L+1,i.value.length);if((S!==_n||L<l.value)&&(S!==jn||A>a.value)){const F=O(l.value)-O(L),q=O(A)-O(a.value);Math.max(F,q)>Ce?(l.value=L,a.value=A):(L<=0&&(l.value=L),A>=i.value.length&&(a.value=A))}o.value=O(l.value),u.value=O(i.value.length)-O(a.value)}function se(d){const S=O(d);!c.value||d&&!S?w=d:c.value.scrollTop=S}const g=p(()=>i.value.slice(l.value,a.value).map((d,S)=>({raw:d,index:S+l.value,key:Gt(d)&&"value"in d?d.value:S+l.value})));return te(i,()=>{f=Array.from({length:i.value.length}),s=Array.from({length:i.value.length}),P.immediate(),W()},{deep:!0}),{calculateVisibleItems:W,containerRef:c,markerRef:v,computedItems:g,paddingTop:o,paddingBottom:u,scrollToIndex:se,handleScroll:T,handleScrollend:z,handleItemResize:E}}function Un(e,i){let t=e.length-1,n=0,l=0,a=null,o=-1;if(e[t]<i)return t;for(;n<=t;)if(l=n+t>>1,a=e[l],a>i)t=l-1;else if(a<i)o=l,n=l+1;else return a===i?l:n;return o}const Kn=N({items:{type:Array,default:()=>[]},renderless:Boolean,...Hn(),...oe(),...Oe()},"VVirtualScroll"),$n=X()({name:"VVirtualScroll",props:Kn(),setup(e,i){let{slots:t}=i;const n=ze("VVirtualScroll"),{dimensionStyles:l}=Le(e),{calculateVisibleItems:a,containerRef:o,markerRef:u,handleScroll:c,handleScrollend:v,handleItemResize:V,scrollToIndex:C,paddingTop:b,paddingBottom:k,computedItems:r}=Nn(e,D(e,"items"));return qt(()=>e.renderless,()=>{function f(){var w,I;const h=(arguments.length>0&&arguments[0]!==void 0?arguments[0]:!1)?"addEventListener":"removeEventListener";o.value===document.documentElement?(document[h]("scroll",c,{passive:!0}),document[h]("scrollend",v)):((w=o.value)==null||w[h]("scroll",c,{passive:!0}),(I=o.value)==null||I[h]("scrollend",v))}zt(()=>{o.value=nn(n.vnode.el,!0),f(!0)}),ut(f)}),J(()=>{const f=r.value.map(s=>m(Fn,{key:s.key,renderless:e.renderless,"onUpdate:height":h=>V(s.index,h)},{default:h=>{var w;return(w=t.default)==null?void 0:w.call(t,{item:s.raw,index:s.index,...h})}}));return e.renderless?m(ie,null,[m("div",{ref:u,class:"v-virtual-scroll__spacer",style:{paddingTop:pe(b.value)}},null),f,m("div",{class:"v-virtual-scroll__spacer",style:{paddingBottom:pe(k.value)}},null)]):m("div",{ref:o,class:["v-virtual-scroll",e.class],onScrollPassive:c,onScrollend:v,style:[l.value,e.style]},[m("div",{ref:u,class:"v-virtual-scroll__container",style:{paddingTop:pe(b.value),paddingBottom:pe(k.value)}},[f])])}),{calculateVisibleItems:a,scrollToIndex:C}}});function Gn(e,i){const t=K(!1);let n;function l(u){cancelAnimationFrame(n),t.value=!0,n=requestAnimationFrame(()=>{n=requestAnimationFrame(()=>{t.value=!1})})}async function a(){await new Promise(u=>requestAnimationFrame(u)),await new Promise(u=>requestAnimationFrame(u)),await new Promise(u=>requestAnimationFrame(u)),await new Promise(u=>{if(t.value){const c=te(t,()=>{c(),u()})}else u()})}async function o(u){var V,C;if(u.key==="Tab"&&((V=i.value)==null||V.focus()),!["PageDown","PageUp","Home","End"].includes(u.key))return;const c=(C=e.value)==null?void 0:C.$el;if(!c)return;(u.key==="Home"||u.key==="End")&&c.scrollTo({top:u.key==="Home"?0:c.scrollHeight,behavior:"smooth"}),await a();const v=c.querySelectorAll(":scope > :not(.v-virtual-scroll__spacer)");if(u.key==="PageDown"||u.key==="Home"){const b=c.getBoundingClientRect().top;for(const k of v)if(k.getBoundingClientRect().top>=b){k.focus();break}}else{const b=c.getBoundingClientRect().bottom;for(const k of[...v].reverse())if(k.getBoundingClientRect().bottom<=b){k.focus();break}}}return{onScrollPassive:l,onKeydown:o}}const qn=N({chips:Boolean,closableChips:Boolean,closeText:{type:String,default:"$vuetify.close"},openText:{type:String,default:"$vuetify.open"},eager:Boolean,hideNoData:Boolean,hideSelected:Boolean,listProps:{type:Object},menu:Boolean,menuIcon:{type:Q,default:"$dropdown"},menuProps:{type:Object},multiple:Boolean,noDataText:{type:String,default:"$vuetify.noDataText"},openOnClear:Boolean,itemColor:String,...ht({itemChildren:!1})},"Select"),zn=N({...qn(),...ge(It({modelValue:null,role:"combobox"}),["validationValue","dirty","appendInnerIcon"]),...Jt({transition:{component:st}})},"VSelect"),Zn=X()({name:"VSelect",props:zn(),emits:{"update:focused":e=>!0,"update:modelValue":e=>!0,"update:menu":e=>!0},setup(e,i){let{slots:t}=i;const{t:n}=Wt(),l=M(),a=M(),o=M(),u=le(e,"menu"),c=p({get:()=>u.value,set:g=>{var d;u.value&&!g&&((d=a.value)!=null&&d.ΨopenChildren.size)||(u.value=g)}}),{items:v,transformIn:V,transformOut:C}=Tn(e),b=le(e,"modelValue",[],g=>V(g===null?[null]:Te(g)),g=>{const d=C(g);return e.multiple?d:d[0]??null}),k=p(()=>typeof e.counterValue=="function"?e.counterValue(b.value):typeof e.counterValue=="number"?e.counterValue:b.value.length),r=Ct(e),f=p(()=>b.value.map(g=>g.value)),s=K(!1),h=p(()=>c.value?e.closeText:e.openText);let w="",I;const P=p(()=>e.hideSelected?v.value.filter(g=>!b.value.some(d=>e.valueComparator(d,g))):v.value),B=p(()=>e.hideNoData&&!P.value.length||r.isReadonly.value||r.isDisabled.value),E=p(()=>{var g;return{...e.menuProps,activatorProps:{...((g=e.menuProps)==null?void 0:g.activatorProps)||{},"aria-haspopup":"listbox"}}}),O=M(),ne=Gn(O,l);function Y(g){e.openOnClear&&(c.value=!0)}function G(){B.value||(c.value=!c.value)}function Z(g){_e(g)&&j(g)}function j(g){var L,y;if(!g.key||r.isReadonly.value)return;["Enter"," ","ArrowDown","ArrowUp","Home","End"].includes(g.key)&&g.preventDefault(),["Enter","ArrowDown"," "].includes(g.key)&&(c.value=!0),["Escape","Tab"].includes(g.key)&&(c.value=!1),g.key==="Home"?(L=O.value)==null||L.focus("first"):g.key==="End"&&((y=O.value)==null||y.focus("last"));const d=1e3;if(!_e(g))return;const S=performance.now();S-I>d&&(w=""),w+=g.key.toLowerCase(),I=S;const x=v.value.find(A=>A.title.toLowerCase().startsWith(w));if(x!==void 0){b.value=[x];const A=P.value.indexOf(x);fe&&window.requestAnimationFrame(()=>{var F;A>=0&&((F=o.value)==null||F.scrollToIndex(A))})}}function T(g){let d=arguments.length>1&&arguments[1]!==void 0?arguments[1]:!0;if(!g.props.disabled)if(e.multiple){const S=b.value.findIndex(L=>e.valueComparator(L.value,g.value)),x=d??!~S;if(~S){const L=x?[...b.value,g]:[...b.value];L.splice(S,1),b.value=L}else x&&(b.value=[...b.value,g])}else{const S=d!==!1;b.value=S?[g]:[],Be(()=>{c.value=!1})}}function z(g){var d;(d=O.value)!=null&&d.$el.contains(g.relatedTarget)||(c.value=!1)}function ue(){var g;e.eager&&((g=o.value)==null||g.calculateVisibleItems())}function W(){var g;s.value&&((g=l.value)==null||g.focus())}function re(g){s.value=!0}function se(g){if(g==null)b.value=[];else if(je(l.value,":autofill")||je(l.value,":-webkit-autofill")){const d=v.value.find(S=>S.title===g);d&&T(d)}else l.value&&(l.value.value="")}return te(c,()=>{if(!e.hideSelected&&c.value&&b.value.length){const g=P.value.findIndex(d=>b.value.some(S=>e.valueComparator(S.value,d.value)));fe&&window.requestAnimationFrame(()=>{var d;g>=0&&((d=o.value)==null||d.scrollToIndex(g))})}}),te(()=>e.items,(g,d)=>{c.value||s.value&&!d.length&&g.length&&(c.value=!0)}),J(()=>{const g=!!(e.chips||t.chip),d=!!(!e.hideNoData||P.value.length||t["prepend-item"]||t["append-item"]||t["no-data"]),S=b.value.length>0,x=Me.filterProps(e),L=S||!s.value&&e.label&&!e.persistentPlaceholder?void 0:e.placeholder;return m(Me,$({ref:l},x,{modelValue:b.value.map(y=>y.props.value).join(", "),"onUpdate:modelValue":se,focused:s.value,"onUpdate:focused":y=>s.value=y,validationValue:b.externalValue,counterValue:k.value,dirty:S,class:["v-select",{"v-select--active-menu":c.value,"v-select--chips":!!e.chips,[`v-select--${e.multiple?"multiple":"single"}`]:!0,"v-select--selected":b.value.length,"v-select--selection-slot":!!t.selection},e.class],style:e.style,inputmode:"none",placeholder:L,"onClick:clear":Y,"onMousedown:control":G,onBlur:z,onKeydown:j,"aria-label":n(h.value),title:n(h.value)}),{...t,default:()=>m(ie,null,[m(Mn,$({ref:a,modelValue:c.value,"onUpdate:modelValue":y=>c.value=y,activator:"parent",contentClass:"v-select__content",disabled:B.value,eager:e.eager,maxHeight:310,openOnClick:!1,closeOnContentClick:!1,transition:e.transition,onAfterEnter:ue,onAfterLeave:W},E.value),{default:()=>[d&&m(En,$({ref:O,selected:f.value,selectStrategy:e.multiple?"independent":"single-independent",onMousedown:y=>y.preventDefault(),onKeydown:Z,onFocusin:re,tabindex:"-1","aria-live":"polite",color:e.itemColor??e.color},ne,e.listProps),{default:()=>{var y,A,F;return[(y=t["prepend-item"])==null?void 0:y.call(t),!P.value.length&&!e.hideNoData&&(((A=t["no-data"])==null?void 0:A.call(t))??m(we,{key:"no-data",title:n(e.noDataText)},null)),m($n,{ref:o,renderless:!0,items:P.value},{default:q=>{var U;let{item:H,index:ae,itemRef:_}=q;const ce=$(H.props,{ref:_,key:H.value,onClick:()=>T(H,null)});return((U=t.item)==null?void 0:U.call(t,{item:H,index:ae,props:ce}))??m(we,$(ce,{role:"option"}),{prepend:St=>{let{isSelected:kt}=St;return m(ie,null,[e.multiple&&!e.hideSelected?m(sn,{key:H.value,modelValue:kt,ripple:!1,tabindex:"-1"},null):void 0,H.props.prependAvatar&&m(Ie,{image:H.props.prependAvatar},null),H.props.prependIcon&&m(ke,{icon:H.props.prependIcon},null)])}})}}),(F=t["append-item"])==null?void 0:F.call(t)]}})]}),b.value.map((y,A)=>{function F(_){_.stopPropagation(),_.preventDefault(),T(y,!1)}const q={"onClick:close":F,onKeydown(_){_.key!=="Enter"&&_.key!==" "||(_.preventDefault(),_.stopPropagation(),F(_))},onMousedown(_){_.preventDefault(),_.stopPropagation()},modelValue:!0,"onUpdate:modelValue":void 0},H=g?!!t.chip:!!t.selection,ae=H?Xt(g?t.chip({item:y,index:A,props:q}):t.selection({item:y,index:A})):void 0;if(!(H&&!ae))return m("div",{key:y.value,class:"v-select__selection"},[g?t.chip?m(ve,{key:"chip-defaults",defaults:{VChip:{closable:e.closableChips,size:"small",text:y.title}}},{default:()=>[ae]}):m(an,$({key:"chip",closable:e.closableChips,size:"small",text:y.title,disabled:y.props.disabled},q),null):ae??m("span",{class:"v-select__selection-text"},[y.title,e.multiple&&A<b.value.length-1&&m("span",{class:"v-select__selection-comma"},[Yt(",")])])])})]),"append-inner":function(){var q;for(var y=arguments.length,A=new Array(y),F=0;F<y;F++)A[F]=arguments[F];return m(ie,null,[(q=t["append-inner"])==null?void 0:q.call(t,...A),e.menuIcon?m(ke,{class:"v-select__menu-icon",icon:e.menuIcon},null):void 0])}})}),$e({isFocused:s,menu:c,select:T},l)}});export{we as V,Vn as a,En as b,Mn as c,Zn as d};
