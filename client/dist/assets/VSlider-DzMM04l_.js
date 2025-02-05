import{G as X,S as n,cU as le,J,W as R,N as ae,q as G,T as he,a2 as ke,a1 as ye,cI as ie,a8 as Se,av as pe,E as Q,R as ge,bp as ue,cV as Ve,cK as we,a7 as Ce,X as Z,cH as q,a as i,w as ne,j as _e,v as Te,a4 as oe,cW as xe,cQ as se,H as Fe,C as Pe,F as Re}from"./index-B0k6gdhc.js";import{j as Ee,u as Me,V as re,m as ze,k as Le,a as Ne}from"./VTextField-BmhlGUcC.js";const ee=Symbol.for("vuetify:v-slider");function Be(e,t,a){const o=a==="vertical",c=t.getBoundingClientRect(),k="touches"in e?e.touches[0]:e;return o?k.clientY-(c.top+c.height/2):k.clientX-(c.left+c.width/2)}function De(e,t){return"touches"in e&&e.touches.length?e.touches[0][t]:"changedTouches"in e&&e.changedTouches.length?e.changedTouches[0][t]:e[t]}const Ie=X({disabled:{type:Boolean,default:null},error:Boolean,readonly:{type:Boolean,default:null},max:{type:[Number,String],default:100},min:{type:[Number,String],default:0},step:{type:[Number,String],default:0},thumbColor:String,thumbLabel:{type:[Boolean,String],default:void 0,validator:e=>typeof e=="boolean"||e==="always"},thumbSize:{type:[Number,String],default:20},showTicks:{type:[Boolean,String],default:!1,validator:e=>typeof e=="boolean"||e==="always"},ticks:{type:[Array,Object]},tickSize:{type:[Number,String],default:2},color:String,trackColor:String,trackFillColor:String,trackSize:{type:[Number,String],default:4},direction:{type:String,default:"horizontal",validator:e=>["vertical","horizontal"].includes(e)},reverse:Boolean,...ye(),...ke({elevation:2}),ripple:{type:Boolean,default:!0}},"Slider"),qe=e=>{const t=n(()=>parseFloat(e.min)),a=n(()=>parseFloat(e.max)),o=n(()=>+e.step>0?parseFloat(e.step):0),c=n(()=>Math.max(le(o.value),le(t.value)));function k(y){if(y=parseFloat(y),o.value<=0)return y;const v=ie(y,t.value,a.value),S=t.value%o.value,_=Math.round((v-S)/o.value)*o.value+S;return parseFloat(Math.min(_,a.value).toFixed(c.value))}return{min:t,max:a,step:o,decimals:c,roundValue:k}},Ke=e=>{let{props:t,steps:a,onSliderStart:o,onSliderMove:c,onSliderEnd:k,getActiveThumb:y}=e;const{isRtl:v}=J(),S=R(t,"reverse"),_=n(()=>t.direction==="vertical"),T=n(()=>_.value!==S.value),{min:f,max:g,step:x,decimals:L,roundValue:E}=a,D=n(()=>parseInt(t.thumbSize,10)),N=n(()=>parseInt(t.tickSize,10)),M=n(()=>parseInt(t.trackSize,10)),F=n(()=>(g.value-f.value)/x.value),I=R(t,"disabled"),P=n(()=>t.error||t.disabled?void 0:t.thumbColor??t.color),u=n(()=>t.error||t.disabled?void 0:t.trackColor??t.color),V=n(()=>t.error||t.disabled?void 0:t.trackFillColor??t.color),m=ae(!1),b=ae(0),w=G(),C=G();function s(l){var te;const r=t.direction==="vertical",ce=r?"top":"left",de=r?"height":"width",ve=r?"clientY":"clientX",{[ce]:me,[de]:be}=(te=w.value)==null?void 0:te.$el.getBoundingClientRect(),fe=De(l,ve);let Y=Math.min(Math.max((fe-me-b.value)/be,0),1)||0;return(r?T.value:T.value!==v.value)&&(Y=1-Y),E(f.value+Y*(g.value-f.value))}const z=l=>{k({value:s(l)}),m.value=!1,b.value=0},B=l=>{C.value=y(l),C.value&&(m.value=!0,C.value.contains(l.target)?b.value=Be(l,C.value,t.direction):(b.value=0,c({value:s(l)})),o({value:s(l)}),Se(()=>{var r;return(r=C.value)==null?void 0:r.focus()}))},p={passive:!0,capture:!0};function K(l){c({value:s(l)})}function A(l){l.stopPropagation(),l.preventDefault(),z(l),window.removeEventListener("mousemove",K,p),window.removeEventListener("mouseup",A)}function U(l){var r;z(l),window.removeEventListener("touchmove",K,p),(r=l.target)==null||r.removeEventListener("touchend",U)}function H(l){var r;B(l),window.addEventListener("touchmove",K,p),(r=l.target)==null||r.addEventListener("touchend",U,{passive:!1})}function h(l){l.preventDefault(),B(l),window.addEventListener("mousemove",K,p),window.addEventListener("mouseup",A,{passive:!1})}const d=l=>{const r=(l-f.value)/(g.value-f.value)*100;return ie(isNaN(r)?0:r,0,100)},O=R(t,"showTicks"),j=n(()=>O.value?t.ticks?Array.isArray(t.ticks)?t.ticks.map(l=>({value:l,position:d(l),label:l.toString()})):Object.keys(t.ticks).map(l=>({value:parseFloat(l),position:d(parseFloat(l)),label:t.ticks[l]})):F.value!==1/0?he(F.value+1).map(l=>{const r=f.value+l*x.value;return{value:r,position:d(r)}}):[]:[]),$=n(()=>j.value.some(l=>{let{label:r}=l;return!!r})),W={activeThumbRef:C,color:R(t,"color"),decimals:L,disabled:I,direction:R(t,"direction"),elevation:R(t,"elevation"),hasLabels:$,isReversed:S,indexFromEnd:T,min:f,max:g,mousePressed:m,numTicks:F,onSliderMousedown:h,onSliderTouchstart:H,parsedTicks:j,parseMouseMove:s,position:d,readonly:R(t,"readonly"),rounded:R(t,"rounded"),roundValue:E,showTicks:O,startOffset:b,step:x,thumbSize:D,thumbColor:P,thumbLabel:R(t,"thumbLabel"),ticks:R(t,"ticks"),tickSize:N,trackColor:u,trackContainerRef:w,trackFillColor:V,trackSize:M,vertical:_};return pe(ee,W),W},Oe=X({focused:Boolean,max:{type:Number,required:!0},min:{type:Number,required:!0},modelValue:{type:Number,required:!0},position:{type:Number,required:!0},ripple:{type:[Boolean,Object],default:!0},name:String,...oe()},"VSliderThumb"),je=Q()({name:"VSliderThumb",directives:{Ripple:ge},props:Oe(),emits:{"update:modelValue":e=>!0},setup(e,t){let{slots:a,emit:o}=t;const c=ue(ee),{isRtl:k,rtlClasses:y}=J();if(!c)throw new Error("[Vuetify] v-slider-thumb must be used inside v-slider or v-range-slider");const{thumbColor:v,step:S,disabled:_,thumbSize:T,thumbLabel:f,direction:g,isReversed:x,vertical:L,readonly:E,elevation:D,mousePressed:N,decimals:M,indexFromEnd:F}=c,I=n(()=>_.value?void 0:D.value),{elevationClasses:P}=Ve(I),{textColorClasses:u,textColorStyles:V}=we(v),{pageup:m,pagedown:b,end:w,home:C,left:s,right:z,down:B,up:p}=Ce,K=[m,b,w,C,s,z,B,p],A=n(()=>S.value?[1,2,3]:[1,5,10]);function U(h,d){if(!K.includes(h.key))return;h.preventDefault();const O=S.value||.1,j=(e.max-e.min)/O;if([s,z,B,p].includes(h.key)){const W=(L.value?[k.value?s:z,x.value?B:p]:F.value!==k.value?[s,p]:[z,p]).includes(h.key)?1:-1,l=h.shiftKey?2:h.ctrlKey?1:0;d=d+W*O*A.value[l]}else if(h.key===C)d=e.min;else if(h.key===w)d=e.max;else{const $=h.key===b?1:-1;d=d-$*O*(j>100?j/10:10)}return Math.max(e.min,Math.min(e.max,d))}function H(h){const d=U(h,e.modelValue);d!=null&&o("update:modelValue",d)}return Z(()=>{const h=q(F.value?100-e.position:e.position,"%");return i("div",{class:["v-slider-thumb",{"v-slider-thumb--focused":e.focused,"v-slider-thumb--pressed":e.focused&&N.value},e.class,y.value],style:[{"--v-slider-thumb-position":h,"--v-slider-thumb-size":q(T.value)},e.style],role:"slider",tabindex:_.value?-1:0,"aria-label":e.name,"aria-valuemin":e.min,"aria-valuemax":e.max,"aria-valuenow":e.modelValue,"aria-readonly":!!E.value,"aria-orientation":g.value,onKeydown:E.value?void 0:H},[i("div",{class:["v-slider-thumb__surface",u.value,P.value],style:{...V.value}},null),ne(i("div",{class:["v-slider-thumb__ripple",u.value],style:V.value},null),[[_e("ripple"),e.ripple,null,{circle:!0,center:!0}]]),i(Ee,{origin:"bottom center"},{default:()=>{var d;return[ne(i("div",{class:"v-slider-thumb__label-container"},[i("div",{class:["v-slider-thumb__label"]},[i("div",null,[((d=a["thumb-label"])==null?void 0:d.call(a,{modelValue:e.modelValue}))??e.modelValue.toFixed(S.value?M.value:1)])])]),[[Te,f.value&&e.focused||f.value==="always"]])]}})])}),{}}}),Ae=X({start:{type:Number,required:!0},stop:{type:Number,required:!0},...oe()},"VSliderTrack"),Ue=Q()({name:"VSliderTrack",props:Ae(),emits:{},setup(e,t){let{slots:a}=t;const o=ue(ee);if(!o)throw new Error("[Vuetify] v-slider-track must be inside v-slider or v-range-slider");const{color:c,parsedTicks:k,rounded:y,showTicks:v,tickSize:S,trackColor:_,trackFillColor:T,trackSize:f,vertical:g,min:x,max:L,indexFromEnd:E}=o,{roundedClasses:D}=xe(y),{backgroundColorClasses:N,backgroundColorStyles:M}=se(T),{backgroundColorClasses:F,backgroundColorStyles:I}=se(_),P=n(()=>`inset-${g.value?"block":"inline"}-${E.value?"end":"start"}`),u=n(()=>g.value?"height":"width"),V=n(()=>({[P.value]:"0%",[u.value]:"100%"})),m=n(()=>e.stop-e.start),b=n(()=>({[P.value]:q(e.start,"%"),[u.value]:q(m.value,"%")})),w=n(()=>v.value?(g.value?k.value.slice().reverse():k.value).map((s,z)=>{var p;const B=s.value!==x.value&&s.value!==L.value?q(s.position,"%"):void 0;return i("div",{key:s.value,class:["v-slider-track__tick",{"v-slider-track__tick--filled":s.position>=e.start&&s.position<=e.stop,"v-slider-track__tick--first":s.value===x.value,"v-slider-track__tick--last":s.value===L.value}],style:{[P.value]:B}},[(s.label||a["tick-label"])&&i("div",{class:"v-slider-track__tick-label"},[((p=a["tick-label"])==null?void 0:p.call(a,{tick:s,index:z}))??s.label])])}):[]);return Z(()=>i("div",{class:["v-slider-track",D.value,e.class],style:[{"--v-slider-track-size":q(f.value),"--v-slider-tick-size":q(S.value)},e.style]},[i("div",{class:["v-slider-track__background",F.value,{"v-slider-track__background--opacity":!!c.value||!T.value}],style:{...V.value,...I.value}},null),i("div",{class:["v-slider-track__fill",N.value],style:{...b.value,...M.value}},null),v.value&&i("div",{class:["v-slider-track__ticks",{"v-slider-track__ticks--always-show":v.value==="always"}]},[w.value])])),{}}}),$e=X({...Le(),...Ie(),...ze(),modelValue:{type:[Number,String],default:0}},"VSlider"),He=Q()({name:"VSlider",props:$e(),emits:{"update:focused":e=>!0,"update:modelValue":e=>!0,start:e=>!0,end:e=>!0},setup(e,t){let{slots:a,emit:o}=t;const c=G(),{rtlClasses:k}=J(),y=qe(e),v=Fe(e,"modelValue",void 0,u=>y.roundValue(u??y.min.value)),{min:S,max:_,mousePressed:T,roundValue:f,onSliderMousedown:g,onSliderTouchstart:x,trackContainerRef:L,position:E,hasLabels:D,readonly:N}=Ke({props:e,steps:y,onSliderStart:()=>{o("start",v.value)},onSliderEnd:u=>{let{value:V}=u;const m=f(V);v.value=m,o("end",m)},onSliderMove:u=>{let{value:V}=u;return v.value=f(V)},getActiveThumb:()=>{var u;return(u=c.value)==null?void 0:u.$el}}),{isFocused:M,focus:F,blur:I}=Me(e),P=n(()=>E(v.value));return Z(()=>{const u=re.filterProps(e),V=!!(e.label||a.label||a.prepend);return i(re,Pe({class:["v-slider",{"v-slider--has-labels":!!a["tick-label"]||D.value,"v-slider--focused":M.value,"v-slider--pressed":T.value,"v-slider--disabled":e.disabled},k.value,e.class],style:e.style},u,{focused:M.value}),{...a,prepend:V?m=>{var b,w;return i(Re,null,[((b=a.label)==null?void 0:b.call(a,m))??(e.label?i(Ne,{id:m.id.value,class:"v-slider__label",text:e.label},null):void 0),(w=a.prepend)==null?void 0:w.call(a,m)])}:void 0,default:m=>{let{id:b,messagesId:w}=m;return i("div",{class:"v-slider__container",onMousedown:N.value?void 0:g,onTouchstartPassive:N.value?void 0:x},[i("input",{id:b.value,name:e.name||b.value,disabled:!!e.disabled,readonly:!!e.readonly,tabindex:"-1",value:v.value},null),i(Ue,{ref:L,start:0,stop:P.value},{"tick-label":a["tick-label"]}),i(je,{ref:c,"aria-describedby":w.value,focused:M.value,min:S.value,max:_.value,modelValue:v.value,"onUpdate:modelValue":C=>v.value=C,position:P.value,elevation:e.elevation,onFocus:F,onBlur:I,ripple:e.ripple,name:e.name},{"thumb-label":a["thumb-label"]})])}})}),{}}});export{He as V};
