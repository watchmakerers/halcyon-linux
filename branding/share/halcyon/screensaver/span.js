// KWin script loaded by halcyon-screensaver while a Windows screensaver runs
// on several monitors: each copy runs in its own Wine desktop window titled
// "HalcyonSaverN"; put window N fullscreen on monitor N (monitors counted
// left to right, then top to bottom).
function screensLeftToRight() {
    return workspace.screens.slice().sort(function (a, b) {
        return a.geometry.x - b.geometry.x || a.geometry.y - b.geometry.y;
    });
}

function place(w) {
    var m = /HalcyonSaver(\d+)/.exec(w.caption || "");
    if (!m) return;
    var s = screensLeftToRight()[parseInt(m[1], 10)];
    if (!s) return;
    w.noBorder = true;
    w.keepAbove = true;
    w.skipTaskbar = true;
    w.skipSwitcher = true;
    if (w.output !== s) {
        w.fullScreen = false;           // Wine makes it fullscreen on the main monitor first
        workspace.sendClientToScreen(w, s);
    }
    w.fullScreen = true;
    if (parseInt(m[1], 10) === 0) workspace.activeWindow = w;
}

workspace.windowAdded.connect(function (w) {
    place(w);
    // Wine sets the title just after mapping the window.
    w.captionChanged.connect(function () { place(w); });
});
workspace.windowList().forEach(place);
