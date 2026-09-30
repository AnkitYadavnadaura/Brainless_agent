"""Runtime-owned DOM strategies; user strings are supplied only as JSON data."""

YOUTUBE_INSPECT = r"""(async () => {
    const step = s => typeof __fleet_step === 'function' ? __fleet_step(s) : console.log('[Brainless] '+s);
    step('youtube.inspect.origin');
    if (!['www.youtube.com','youtube.com','m.youtube.com','music.youtube.com'].includes(location.hostname))
        return {ok:false,error:'YouTube is not the current page'};
    const visible = e => e && e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden';
    step('youtube.inspect.wait_for_video');
    for (let i=0; i<24; i++) {
        const video = [...document.querySelectorAll('video')].find(visible);
        if (video && /^\/(watch|live|shorts)(\/|$)/.test(location.pathname)) {
            step('youtube.inspect.player_found'); return {ok:true,video:true};
        }
        const links = [...document.querySelectorAll(
            'ytd-video-renderer a#video-title, ytd-rich-item-renderer a#thumbnail, a.yt-lockup-view-model__content-image')];
        const link = links.find(e => visible(e) && new URL(e.href).hostname === location.hostname
            && /^\/(watch|shorts|live)(\/|$)/.test(new URL(e.href).pathname));
        if (link) { step('youtube.inspect.result_found'); return {ok:true,url:link.href}; }
        await new Promise(r => setTimeout(r,250));
    }
    step('youtube.inspect.no_result');
    return {ok:false,error:'No visible YouTube video or result; check sign-in/consent or choose a video'};
})()"""

YOUTUBE_PLAY = r"""(async () => {
    const step = s => typeof __fleet_step === 'function' ? __fleet_step(s) : console.log('[Brainless] '+s);
    step('youtube.play.origin');
    if (!['www.youtube.com','youtube.com','m.youtube.com','music.youtube.com'].includes(location.hostname)
        || !/^\/(watch|live|shorts)(\/|$)/.test(location.pathname))
        return {ok:false,error:'The selected YouTube video page changed'};
    step('youtube.play.wait_for_player');
    for (let i=0; i<24; i++) {
        const video = [...document.querySelectorAll('video')].find(e => e.getClientRects().length);
        if (video) {
            try { if (video.paused) { step('youtube.play.activate'); await video.play(); } }
            catch (e) { step('youtube.play.blocked'); return {ok:false,error:'Playback requires user interaction: '+e.name}; }
            const before = video.currentTime;
            await new Promise(r => setTimeout(r,500));
            if (!video.paused && !video.ended && video.readyState >= 2 && video.currentTime > before) {
                step('youtube.play.verified');
                return {ok:true,playing:true};
            }
        }
        await new Promise(r => setTimeout(r,250));
    }
    step('youtube.play.unverified');
    return {ok:false,error:'Video playback was not verified'};
})()"""

GMAIL_SEND = r"""(async () => {
    const step = s => typeof __fleet_step === 'function' ? __fleet_step(s) : console.log('[Brainless] '+s);
    const payload = __PAYLOAD__;
    let submitted = false;
    const visible = e => e && e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden';
    const sleep = ms => new Promise(r => setTimeout(r,ms));
    const one = (root, selector) => {
        const found = [...root.querySelectorAll(selector)].filter(visible);
        if (found.length !== 1) throw Error('Missing or ambiguous Gmail draft control');
        return found[0];
    };
    const set = (el, value) => {
        el.focus();
        if ('value' in el) {
            const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
            Object.getOwnPropertyDescriptor(proto, 'value').set.call(el,value);
        } else el.textContent = value;
        el.dispatchEvent(new Event('input',{bubbles:true}));
        el.dispatchEvent(new Event('change',{bubbles:true}));
    };
    try {
        step('gmail.origin.verify');
        if (location.protocol !== 'https:' || location.hostname !== 'mail.google.com')
            return {ok:false,sent:false,error:'login_required'};
        // Reuse only one unambiguous compose form; never overwrite an unrelated draft.
        step('gmail.compose.inspect');
        let subjects = [...document.querySelectorAll('input[name="subjectbox"]')].filter(visible);
        if (!subjects.length) {
            step('gmail.compose.open');
            one(document, 'div[gh="cm"], button[aria-label="Compose"]').click();
            for (let i=0; i<20 && !subjects.length; i++) {
                await sleep(200);
                subjects = [...document.querySelectorAll('input[name="subjectbox"]')].filter(visible);
            }
        }
        if (subjects.length !== 1) throw Error('Missing or ambiguous compose window');
        const subject = subjects[0];
        const form = subject.closest('form');
        if (!form) throw Error('Gmail compose form was not found');
        const body = one(form, '[contenteditable="true"][role="textbox"]');
        const normalize = s => s.replace(/\r\n/g,'\n').trim();
        const bodyText = () => body.innerText || body.textContent || '';
        if ((subject.value && subject.value !== payload.subject)
            || (normalize(bodyText()) && normalize(bodyText()) !== normalize(payload.body)))
            throw Error('Existing Gmail draft differs from the approved message');
        const chips = () => [...form.querySelectorAll('[email],[data-hovercard-id]')]
            .map(e => e.getAttribute('email') || e.getAttribute('data-hovercard-id')).filter(Boolean);
        step('gmail.recipient.inspect');
        if (chips().some(email => email !== payload.to)) throw Error('Draft has another recipient');
        const extra = [...form.querySelectorAll('input[name="cc"],input[name="bcc"],textarea[name="cc"],textarea[name="bcc"]')];
        if (extra.some(e => e.value.trim())) throw Error('Draft has additional recipients');
        if (!chips().includes(payload.to)) {
            const to = one(form, 'input[name="to"],textarea[name="to"],input[aria-label="To recipients"]');
            if (to.value && to.value !== payload.to) throw Error('Draft has another pending recipient');
            step('gmail.recipient.fill');
            set(to,payload.to);
            step('gmail.recipient.commit');
            to.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',code:'Enter',keyCode:13,which:13,bubbles:true}));
            to.dispatchEvent(new KeyboardEvent('keyup',{key:'Enter',code:'Enter',keyCode:13,which:13,bubbles:true}));
            for (let i=0; i<20 && !chips().includes(payload.to); i++) await sleep(150);
        }
        step('gmail.subject.fill'); set(subject,payload.subject);
        step('gmail.body.fill'); set(body,payload.body);
        await sleep(250);
        step('gmail.draft.verify');
        const recipients = [...new Set(chips())];
        if (recipients.length !== 1 || recipients[0] !== payload.to
            || subject.value !== payload.subject || normalize(bodyText()) !== normalize(payload.body))
            throw Error('Gmail did not confirm the exact approved draft');
        const send = one(form, '[role="button"][aria-label^="Send"],button[aria-label^="Send"]');
        const alreadySent = [...document.querySelectorAll('[role="alert"],[role="status"]')]
            .filter(e => visible(e) && /Message sent/i.test(e.textContent));
        if (alreadySent.length) throw Error('A prior send notification is still visible; inspect before retrying');
        submitted = true;
        step('gmail.send.activate');
        send.click();
        step('gmail.send.wait_for_confirmation');
        for (let i=0; i<40; i++) {
            if ([...document.querySelectorAll('[role="alert"],[role="status"]')]
                .some(e => visible(e) && /Message sent/i.test(e.textContent))) {
                step('gmail.send.verified'); return {ok:true,sent:true};
            }
            await sleep(250);
        }
        step('gmail.send.unconfirmed');
        return {ok:false,sent:true,error:'Send activated but confirmation not observed'};
    } catch(e) { step(submitted?'gmail.failed_after_send':'gmail.failed_before_send'); return {ok:false,sent:submitted,error:String(e.message)}; }
})()"""
