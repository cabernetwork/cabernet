(function (playbackManager, focusManager, appRouter, dom) {
    "use strict";
    var lastInputTime = Date.now();
    function notify() {
        (lastInputTime = Date.now()), handleCommand("unknown");
    }
    var commandTimes = {};
    function handleCommand(name, options) {
        lastInputTime = Date.now();
        var tagName,
            sourceElement = options ? options.sourceElement : null;
        ((sourceElement = sourceElement || document.activeElement) && "BODY" !== (tagName = sourceElement.tagName) && "HTML" !== tagName) || (sourceElement = focusManager.getCurrentScope());
        var command,
            last,
            now,
            customEvent = new CustomEvent("command", { detail: { command: name }, bubbles: !0, cancelable: !0 });
        if (!sourceElement.dispatchEvent(customEvent)) return !0;
        switch (name) {
            case "up":
                return focusManager.moveUp(sourceElement), !0;
            case "down":
                return focusManager.moveDown(sourceElement), !0;
            case "left":
                return focusManager.moveLeft(sourceElement), !0;
            case "right":
                return focusManager.moveRight(sourceElement), !0;
            case "home":
                return appRouter.goHome(), !0;
            case "settings":
                return appRouter.showSettings(), !0;
            case "back":
                return appRouter.back(), !0;
            case "forward":
                return !0;
            case "select":
                return sourceElement.click(), !0;
            case "menu":
            case "info":
                return !0;
            case "nextchapter":
                return playbackManager.nextChapter(), !0;
            case "next":
            case "nexttrack":
                return playbackManager.nextTrack(), !0;
            case "previous":
            case "previoustrack":
                return playbackManager.previousTrack(), !0;
            case "previouschapter":
                return playbackManager.previousChapter(), !0;
            case "guide":
                return appRouter.showGuide(), !0;
            case "recordedtv":
                return appRouter.showRecordedTV(), !0;
            case "record":
                return !0;
            case "livetv":
                return appRouter.showLiveTV(), !0;
            case "mute":
                return playbackManager.setMute(!0), !0;
            case "unmute":
                return playbackManager.setMute(!1), !0;
            case "togglemute":
                return playbackManager.toggleMute(), !0;
            case "channelup":
                return playbackManager.channelUp(), !0;
            case "channeldown":
                return playbackManager.channelDown(), !0;
            case "volumedown":
                return playbackManager.volumeDown(), !0;
            case "volumeup":
                return playbackManager.volumeUp(), !0;
            case "play":
                return playbackManager.unpause(), !0;
            case "pause":
                return playbackManager.pause(), !0;
            case "playpause":
                return playbackManager.playPause(), !0;
            case "stop":
                return (last = commandTimes[(command = "stop")] || 0), (now = Date.now()) - last < 1e3 || ((commandTimes[command] = now), !1) || playbackManager.stop(), !0;
            case "changezoom":
                return playbackManager.toggleAspectRatio(), !0;
            case "changeaudiotrack":
                return playbackManager.changeAudioStream(), !0;
            case "changesubtitletrack":
                return playbackManager.changeSubtitleStream(), !0;
            case "search":
                return appRouter.showSearch(), !0;
            case "favorites":
                return appRouter.showFavorites(), !0;
            case "fastforward":
                return playbackManager.fastForward(), !0;
            case "rewind":
                return playbackManager.rewind(), !0;
            case "togglefullscreen":
                return playbackManager.toggleFullscreen(), !0;
            case "disabledisplaymirror":
                return playbackManager.enableDisplayMirroring(!1), !0;
            case "enabledisplaymirror":
                return playbackManager.enableDisplayMirroring(!0), !0;
            case "toggledisplaymirror":
                return playbackManager.toggleDisplayMirroring(), !0;
            case "togglestats":
                return !0;
            case "movies":
            case "music":
            case "tv":
                return appRouter.goHome(), !0;
            case "nowplaying":
                return appRouter.showNowPlaying(), !0;
            case "save":
            case "screensaver":
            case "refresh":
            case "changebrightness":
            case "red":
            case "green":
            case "yellow":
            case "blue":
            case "grey":
            case "brown":
                return !0;
            case "repeatnone":
                return playbackManager.setRepeatMode("RepeatNone"), !0;
            case "repeatall":
                return playbackManager.setRepeatMode("RepeatAll"), !0;
            case "repeatone":
                return playbackManager.setRepeatMode("RepeatOne"), !0;
            default:
                return !1;
        }
    }
    return (
        dom.addEventListener(document, "click", notify, { passive: !0 }),
        {
            trigger: handleCommand,
            handle: handleCommand,
            notify: notify,
            notifyMouseMove: function () {
                lastInputTime = Date.now();
            },
            idleTime: function () {
                return Date.now() - lastInputTime;
            },
            on: function (scope, fn) {
                dom.addEventListener(scope, "command", fn, {});
            },
            off: function (scope, fn) {
                dom.removeEventListener(scope, "command", fn, {});
            },
        }
    );
});
