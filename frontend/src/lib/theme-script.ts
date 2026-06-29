// Synchronous <head> script string. Runs before paint to set data-theme and
// avoid a flash of the wrong theme. Resolution order: localStorage → cookie →
// prefers-color-scheme. Keep this dependency-free (it is injected as raw text).
export const THEME_INIT_SCRIPT = `(function(){try{var t=localStorage.getItem('theme');if(!t){var m=document.cookie.match(/(?:^|; )theme=([^;]+)/);if(m){t=decodeURIComponent(m[1]);}}if(t!=='dark'&&t!=='light'){t=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}document.documentElement.setAttribute('data-theme',t);}catch(e){}})();`;
