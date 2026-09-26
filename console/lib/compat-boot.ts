// Inline in <head>, before any other script (app/layout.tsx): the array and object methods an older browser lacks, the
// owner's iOS 15 phone among them. A browser that has them is left alone. Kept apart from lib/compat.ts so the root layout
// pulls no markdown library into the server bundle.
export const COMPAT_BOOT = `(function(){var A=Array.prototype;
if(!A.toSorted)A.toSorted=function(c){return this.slice().sort(c)};
if(!A.toReversed)A.toReversed=function(){return this.slice().reverse()};
if(!A.toSpliced)A.toSpliced=function(){var a=this.slice();a.splice.apply(a,arguments);return a};
if(!A.with)A.with=function(i,v){var a=this.slice();a[i<0?a.length+i:i]=v;return a};
if(!A.findLast)A.findLast=function(f,t){for(var i=this.length-1;i>=0;i--)if(f.call(t,this[i],i,this))return this[i]};
if(!A.findLastIndex)A.findLastIndex=function(f,t){for(var i=this.length-1;i>=0;i--)if(f.call(t,this[i],i,this))return i;return-1};
if(!Object.hasOwn)Object.hasOwn=function(o,k){return Object.prototype.hasOwnProperty.call(o,k)};
if(!("structuredClone" in window))window.structuredClone=function(v){return JSON.parse(JSON.stringify(v))};
})();`;
