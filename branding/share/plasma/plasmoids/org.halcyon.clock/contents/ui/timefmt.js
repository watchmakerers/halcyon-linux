.pragma library

// Times and dates the way the clock shows them. A Date shifted by a zone's
// offset is read with the getUTC* methods, so the computer's own zone
// never leaks in.

const DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
                "October", "November", "December"]

function pad(n) { return (n < 10 ? "0" : "") + n }

// Wall-clock fields for a zone `offset` seconds from UTC.
function inZone(now, offset) {
    const d = new Date(now.getTime() + offset * 1000)
    return { h: d.getUTCHours(), m: d.getUTCMinutes(), s: d.getUTCSeconds(), ms: d.getUTCMilliseconds(),
             day: d.getUTCDate(), month: d.getUTCMonth(), year: d.getUTCFullYear(), weekday: d.getUTCDay() }
}

function time(t, use24, seconds) {
    const sec = seconds ? ":" + pad(t.s) : ""
    if (use24)
        return pad(t.h) + ":" + pad(t.m) + sec
    return ((t.h % 12) || 12) + ":" + pad(t.m) + sec + (t.h < 12 ? " AM" : " PM")
}

function shortDate(t) { return (t.month + 1) + "/" + t.day + "/" + t.year }

function longDate(t) { return DAYS[t.weekday] + ", " + MONTHS[t.month] + " " + t.day + ", " + t.year }

// "Today", "Tomorrow" or "Yesterday" for another zone compared with here.
function dayWord(t, here) {
    const a = Date.UTC(t.year, t.month, t.day), b = Date.UTC(here.year, here.month, here.day)
    return a > b ? "Tomorrow" : a < b ? "Yesterday" : "Today"
}
