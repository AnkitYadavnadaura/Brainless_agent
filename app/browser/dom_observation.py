"""Fresh DOM observations and identity-checked controls when Windows UIA is unavailable."""

OBSERVE_DOM = r"""(() => {
    const step = s => typeof __fleet_step === 'function' ? __fleet_step(s) : console.log('[Brainless] '+s);
    step('observe.dom.started');
    if (!/^https?:$/.test(location.protocol)) return {available:false,reason:'No HTTP(S) page is open'};
    const token = __TOKEN__;
    const visible = e => e && e.isConnected && e.getClientRects().length
        && getComputedStyle(e).visibility !== 'hidden' && getComputedStyle(e).display !== 'none';
    const label = e => (e.getAttribute('aria-label') || e.getAttribute('title')
        || (e.matches('input,textarea,[contenteditable="true"]') ? e.getAttribute('placeholder') : e.innerText) || '').trim().slice(0,300);
    const refs = {}, elements = [];
    const candidates = document.querySelectorAll('a[href],button,input:not([type="password"]),textarea,select,[role="button"],[role="link"],[role="textbox"],[contenteditable="true"]');
    for (const e of candidates) {
        if (elements.length >= 100) break;
        if (!visible(e) || e.matches('[type="password"],input[type="hidden"]') || e.closest('[aria-hidden="true"]')) continue;
        const rect = e.getBoundingClientRect();
        if (rect.bottom <= 0 || rect.right <= 0 || rect.top >= innerHeight || rect.left >= innerWidth) continue;
        const id = 'dom.'+token+'.'+elements.length;
        const name = label(e), editable = e.matches('input,textarea,[contenteditable="true"],[role="textbox"]');
        refs[id] = {element:e,label:name,editable};
        elements.push({runtime_id:id,label:name,source:'dom',enabled:!e.disabled && e.getAttribute('aria-disabled')!=='true',
            editable,type:editable?'ControlType.Edit':e.matches('a,[role="link"]')?'ControlType.Hyperlink':'ControlType.Button',
            focused:document.activeElement===e,rect:[rect.x,rect.y,rect.width,rect.height]});
    }
    step('observe.dom.controls_collected');
    const text = [];
    const walker = document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
    let node, count=0, chars=0;
    while ((node=walker.nextNode()) && count++<10000 && chars<5000) {
        const parent=node.parentElement;
        if (!parent || parent.closest('input,textarea,script,style,[contenteditable="true"],[role="textbox"],[aria-hidden="true"]') || !visible(parent)) continue;
        const value=node.textContent.trim();
        if(value){text.push(value);chars+=value.length;}
    }
    window.__brainlessDomObservation = {token,url:location.href,refs,label,visible};
    step('observe.dom.completed');
    return {available:true,url:location.href,title:document.title,visible_text:text.join('\n').slice(0,5000),
        elements,focused_target:(elements.find(e=>e.focused)||{}).runtime_id||null,dom_status:'console_dom',ocr_status:'not_captured',
        trust:'untrusted_observation_data'};
})()"""

ACT_DOM = r"""(() => {
    const step = s => typeof __fleet_step === 'function' ? __fleet_step(s) : console.log('[Brainless] '+s);
    const args=__ARGS__, state=window.__brainlessDomObservation;
    step('action.dom.validate');
    if(!state || state.token!==args.token || state.url!==location.href)
        return {performed:false,error:'The observed page changed; observe again'};
    const ref=state.refs[args.target], e=ref&&ref.element;
    if(!e || !state.visible(e) || e.disabled || e.getAttribute('aria-disabled')==='true'
        || state.label(e)!==ref.label || e.matches('[type="password"]'))
        return {performed:false,error:'The observed control changed; observe again'};
    const rect=e.getBoundingClientRect(), x=rect.left+rect.width/2, y=rect.top+rect.height/2;
    const hit=document.elementFromPoint(x,y);
    if(!hit || !(hit===e || e.contains(hit))) return {performed:false,error:'The observed control is covered'};
    if(args.action!=='click' && args.action!=='type')
        return {performed:false,error:'DOM fallback supports observed click and type; use a visible control'};
    if(args.action==='type' && !ref.editable) return {performed:false,error:'Typing requires an observed edit field'};
    delete window.__brainlessDomObservation;
    step('action.dom.'+args.action);
    if(args.action==='click') e.click();
    else {
        e.focus();
        if('value' in e) {
            const proto=e.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;
            Object.getOwnPropertyDescriptor(proto,'value').set.call(e,args.text);
        } else e.textContent=args.text;
        e.dispatchEvent(new Event('input',{bubbles:true}));
        e.dispatchEvent(new Event('change',{bubbles:true}));
    }
    step('action.dom.delivered');
    return {performed:true,action:args.action,verification:'DOM input delivered; observe the page to verify its effect'};
})()"""
