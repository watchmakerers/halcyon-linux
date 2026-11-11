#!/usr/bin/env bash
# Build the Halcyon Linux live ISO.
#
#   ./build.sh            build branding package + ISO into ./out
#   ./build.sh --clean    also wipe the previous work directory first
#
# Run as your normal user; it uses sudo for the steps that need root.
set -euo pipefail

HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
WORK=${WORK:-$HERE/work}
OUT=${OUT:-$HERE/out}
PROFILE=$WORK/profile
REPO=$WORK/repo

msg() { printf '\e[38;2;30;155;224m==>\e[0m \e[1m%s\e[0m\n' "$*"; }
die() { printf '\e[31mError:\e[0m %s\n' "$*" >&2; exit 1; }

[[ $EUID -ne 0 ]] || die "Run as a normal user (makepkg refuses root); sudo is used where needed."

# An interrupted mkarchiso leaves the host's /dev, /proc, /sys (and efivars!)
# mounted inside $WORK/build. A plain "rm -rf" then deletes the host's real
# device nodes and UEFI boot entries. So: unmount first, refuse if anything
# is still mounted, and never let rm cross a filesystem boundary.
safe_wipe() {
    local dir=$1 m
    [[ -e $dir ]] || return 0
    dir=$(readlink -f -- "$dir")
    while read -r m; do
        sudo umount -- "$m" || sudo umount -l -- "$m"
    done < <(findmnt -rn -o TARGET | awk -v p="$dir/" 'index($0, p) == 1' | sort -r)
    if findmnt -rn -o TARGET | awk -v p="$dir/" 'index($0, p) == 1' | grep -q .; then
        die "Something is still mounted inside $dir; not deleting it. Reboot, then run ./build.sh again."
    fi
    sudo rm -rf --one-file-system -- "$dir"
}

if pgrep -f "mkarchiso .*-w $WORK/build" >/dev/null; then
    die "A Halcyon build is already running. Wait for it to finish (or stop it) first."
fi

# ------------------------------------------------------------ preflight ---
assets=$HERE/branding/assets
[[ -f $assets/logo.png || -f $assets/logo.svg ]] || die "Put your logo at branding/assets/logo.png (or .svg)."
compgen -G "$assets/wallpapers/*.*" >/dev/null || die "Put at least one wallpaper in branding/assets/wallpapers/."

# grub: mkarchiso builds the ISO's UEFI boot loader with the host's grub tools
# (installing the package doesn't change how this computer boots).
need=()
for p in archiso librsvg imagemagick python grub; do pacman -Q "$p" &>/dev/null || need+=("$p"); done
if ((${#need[@]})); then
    msg "Installing build tools: ${need[*]}"
    sudo pacman -S --needed --noconfirm "${need[@]}"
fi

if [[ ${1:-} == --clean ]]; then
    msg "Cleaning $WORK"
    safe_wipe "$WORK"
fi
mkdir -p "$WORK/sources" "$OUT"

# ------------------------------------------------------ signing keys ---
# The ISO installs from CachyOS's repos, so pacman needs their signing key.
# It goes into a keyring just for the build (GPGDir below); this computer's
# own pacman keyring is left alone.
KEYRING=$WORK/gnupg
CACHY_KEY=882DCFE48E2051D48E2562ABF3B607488DB35A47
if ! sudo pacman-key --gpgdir "$KEYRING" --list-keys "$CACHY_KEY" &>/dev/null; then
    msg "Preparing the build keyring (Arch + CachyOS keys)"
    sudo rm -rf --one-file-system -- "$KEYRING"
    sudo pacman-key --gpgdir "$KEYRING" --init
    sudo pacman-key --gpgdir "$KEYRING" --populate archlinux
    sudo pacman-key --gpgdir "$KEYRING" --add "$HERE/cachyos/cachyos.gpg"
    sudo pacman-key --gpgdir "$KEYRING" --lsign-key "$CACHY_KEY"
fi

# ---------------------------------------------------- branding package ---
msg "Building halcyon-branding package"
rm -rf "$REPO" && mkdir -p "$REPO"
(cd "$HERE/branding" && BUILDDIR="$WORK/makepkg" SRCDEST="$WORK/sources" PKGDEST="$REPO" makepkg -f --nodeps --noconfirm)
pkg=$(ls "$REPO"/halcyon-branding-*.pkg.tar.zst)
repo-add -q "$REPO/halcyon.db.tar.gz" "$pkg"

# ------------------------------------------------------------- profile ---
msg "Assembling archiso profile"
safe_wipe "$PROFILE"
cp -a "${RELENG:-/usr/share/archiso/configs/releng}" "$PROFILE"
air=$PROFILE/airootfs

# Identity
sed -i \
    -e 's/^iso_name=.*/iso_name="halcyon"/' \
    -e 's/^iso_label=.*/iso_label="HALCYON_$(date --date="@${SOURCE_DATE_EPOCH:-$(date +%s)}" +%Y%m)"/' \
    -e 's|^iso_publisher=.*|iso_publisher="Halcyon Linux"|' \
    -e 's|^iso_application=.*|iso_application="Halcyon Linux Live"|' \
    -e 's/^install_dir=.*/install_dir="halcyon"/' \
    "$PROFILE/profiledef.sh"
# xz with the x86 filter: the ISO has to fit in one GitHub release file (2 GiB).
# zstd unpacked faster but left the image ~10% bigger.
sed -i "s/^airootfs_image_tool_options=.*/airootfs_image_tool_options=('-comp' 'xz' '-Xbcj' 'x86' '-b' '1M' '-Xdict-size' '1M')/" \
    "$PROFILE/profiledef.sh"
# UEFI via GRUB, which reads the kernel and initramfs from the ISO itself;
# systemd-boot needed its own copy of both inside the EFI image (~250 MB more).
sed -i "s/'uefi.systemd-boot'/'uefi.grub'/" "$PROFILE/profiledef.sh"
# Leave out translations (English stays), documentation, man pages and
# developer files, here and on installed systems, so updates stay lean too.
noextract='NoExtract = usr/share/locale/* usr/share/doc/* usr/share/man/* usr/share/gir-1.0/* usr/share/qt6/translations/* !usr/share/locale/en/* !usr/share/locale/en_US/* !usr/share/locale/en_GB/* !usr/share/locale/locale.alias'
sed -i "/^\[options\]/a $noextract" "$PROFILE/pacman.conf"
# CachyOS on top of Arch: [cachyos] goes above [core] so its builds (kernel,
# pacman, mesa, gaming bits) win, and [multilib] is on for 32-bit game libs.
# This is the baseline x86-64 repo; halcyon-install adds the v3/v4/Zen 4
# repos the installed machine's CPU can run.
sed -i -e '/^\[core\]$/i [cachyos]\nInclude = /etc/pacman.d/cachyos-mirrorlist\n' \
       -e '/^#\[multilib\]$/,/^#Include/ s/^#//' "$PROFILE/pacman.conf"
# The live/installed system gets the same config (before the build-only bits
# below); pacman leaves an existing /etc/pacman.conf alone.
install -Dm644 "$PROFILE/pacman.conf" "$air/etc/pacman.conf"
echo halcyon > "$air/etc/hostname"

# Build-only: the build keyring, CachyOS mirrors from this repo since the host
# has no /etc/pacman.d/cachyos-mirrorlist, and current Arch mirrors instead of
# the host's list. The host's may be a frozen snapshot (Omarchy's
# stable-mirror is), which falls out of step with CachyOS's always-current repo.
cat > "$WORK/arch-mirrorlist" <<'EOF'
Server = https://geo.mirror.pkgbuild.com/$repo/os/$arch
Server = https://fastly.mirror.pkgbuild.com/$repo/os/$arch
Server = https://mirror.rackspace.com/archlinux/$repo/os/$arch
EOF
sed -i -e "/^\[options\]/a GPGDir = $KEYRING" \
       -e "s|/etc/pacman.d/cachyos-mirrorlist|$HERE/cachyos/cachyos-mirrorlist|" \
       -e "s|^Include = /etc/pacman.d/mirrorlist$|Include = $WORK/arch-mirrorlist|" "$PROFILE/pacman.conf"

# Local repo with the branding package
cat >> "$PROFILE/pacman.conf" <<EOF

[halcyon]
SigLevel = Optional TrustAll
Server = file://$REPO
EOF

# Packages: releng base minus server-ish bits, plus the desktop
sed -i -E '/^(cloud-init|iwd|irssi|lftp|lynx|mc|vpnc|wvdial|xl2tpd|pptpclient|clonezilla|partimage|darkhttpd)$/d' \
    "$PROFILE/packages.x86_64"
# CachyOS kernel instead of Arch's (broadcom-wl is built against Arch's
# 'linux' and would pull it back in).
sed -i -E -e 's/^linux$/linux-cachyos/' -e '/^broadcom-wl$/d' "$PROFILE/packages.x86_64"
{ echo; grep -hEv '^\s*(#|$)' "$HERE/cachyos/packages.txt" "$HERE/branding/desktop-packages.txt"; echo halcyon-branding; } \
    >> "$PROFILE/packages.x86_64"

# archiso's boot entries name the kernel 'linux'. (Older archiso also shipped
# its own linux.preset; newer ones use the kernel package's default preset,
# which mkinitcpio generates for linux-cachyos just the same.)
kfiles=("$PROFILE"/syslinux/*.cfg "$PROFILE"/efiboot/loader/entries/*.conf "$PROFILE"/grub/*.cfg)
if [[ -f $air/etc/mkinitcpio.d/linux.preset ]]; then
    mv "$air/etc/mkinitcpio.d/linux.preset" "$air/etc/mkinitcpio.d/linux-cachyos.preset"
    kfiles+=("$air/etc/mkinitcpio.d/linux-cachyos.preset")
fi
sed -i -E -e 's/vmlinuz-linux\b/vmlinuz-linux-cachyos/g' -e 's/initramfs-linux\.img/initramfs-linux-cachyos.img/g' \
    -e "s/'linux' package/'linux-cachyos' package/" "${kfiles[@]}"

# Services: NetworkManager + SDDM instead of networkd/iwd; graphical boot
wants=$air/etc/systemd/system
rm -f "$wants"/multi-user.target.wants/{systemd-networkd,iwd}.service \
      "$wants"/sockets.target.wants/systemd-networkd.socket \
      "$wants"/network-online.target.wants/systemd-networkd-wait-online.service \
      "$wants"/dbus-org.freedesktop.network1.service
rm -rf "$wants"/cloud-init.target.wants "$wants"/getty@tty1.service.d
ln -sf /usr/lib/systemd/system/NetworkManager.service "$wants/multi-user.target.wants/NetworkManager.service"
ln -sf /usr/lib/systemd/system/NetworkManager-dispatcher.service "$wants/dbus-org.freedesktop.nm-dispatcher.service"
ln -sf /usr/lib/systemd/system/sddm.service "$wants/display-manager.service"
# CachyOS process priorities (games and the desktop over background work)
ln -sf /usr/lib/systemd/system/ananicy-cpp.service "$wants/multi-user.target.wants/ananicy-cpp.service"
ln -sf /usr/lib/systemd/system/graphical.target "$wants/default.target"

# Overlay our live-session files (live user, autologin, installer icon)
cp -a "$HERE/profile/airootfs/." "$air/"
echo 'liveuser:x:1000:100:Live User:/home/liveuser:/bin/bash' >> "$air/etc/passwd"
echo 'liveuser::14871::::::' >> "$air/etc/shadow"
install -Dm644 "$pkg" "$air/usr/share/halcyon/pkgs/$(basename "$pkg")"
sed -i '${/^)$/d}' "$PROFILE/profiledef.sh"
cat >> "$PROFILE/profiledef.sh" <<'EOF'
  ["/etc/sudoers.d"]="0:0:750"
  ["/etc/sudoers.d/liveuser"]="0:0:440"
  ["/etc/skel/Desktop/halcyon-install.desktop"]="0:0:755"
)
EOF

# Plymouth in the live initramfs. No kms hook: it packs every GPU's firmware into
# the initramfs (~150 MB); the splash runs on the kernel's simpledrm until the
# real driver loads from the live system.
sed -i -e 's/\budev\b/udev plymouth/' -e 's/ kms / /' "$air/etc/mkinitcpio.conf.d/archiso.conf"

# Boot menus: names, splash params, theme
for f in "$PROFILE"/syslinux/*.cfg "$PROFILE"/efiboot/loader/entries/*.conf "$PROFILE"/grub/*.cfg; do
    sed -i -e 's/Arch Linux install medium/Halcyon Linux live medium/g' \
           -e 's/Arch Linux/Halcyon Linux/g' "$f"
done
sed -i -E '/archisobasedir=/ { /accessibility=on/! s/%KERNEL_PARAMS%/quiet splash cow_spacesize=4G %KERNEL_PARAMS%/ }' \
    "$PROFILE"/syslinux/*.cfg "$PROFILE"/efiboot/loader/entries/*.conf "$PROFILE"/grub/*.cfg
sed -i -E \
    -e 's/^(MENU COLOR border\s+\S+\s+)\S+ \S+/\1#80c8f0ff #00000000/' \
    -e 's/^(MENU COLOR title\s+\S+\s+)\S+ \S+/\1#ffffffff #00000000/' \
    -e 's/^(MENU COLOR sel\s+\S+\s+)\S+ \S+/\1#ffffffff #c01e9be0/' \
    -e 's/^(MENU COLOR unsel\s+\S+\s+)\S+ \S+/\1#e0ffffff #600a3456/' \
    "$PROFILE/syslinux/archiso_head.cfg"

# BIOS boot menu background: plain sky gradient (no wallpaper)
magick -size 640x480 gradient:'#0a5fa8-#8cd9f8' -depth 8 "PNG24:$PROFILE/syslinux/splash.png"

# ----------------------------------------------------------------- iso ---
msg "Running mkarchiso (this takes a while)"
# mkarchiso skips steps it has finished before; start fresh so changes land.
safe_wipe "$WORK/build"
sudo mkarchiso -v -w "$WORK/build" -o "$OUT" "$PROFILE"
msg "Done: $(ls -t "$OUT"/halcyon-*.iso | head -1)"
