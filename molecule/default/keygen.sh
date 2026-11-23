#!/bin/sh
# Writes throwaway versions of the keys README.md asks the user for:
#
#   $1/onion/hs_ed25519_secret_key   the onion service key
#   $1/i2p/{web,gemini,cgit}.dat     the I2P destination keys
#
# tor and i2pd each create the key of a service whose key file is
# missing, at startup and without the network, so each is started just
# long enough to write them. Keys that already exist are kept, so the
# addresses stay put across converges. Prints "changed" if it wrote any,
# and nothing else unless a step fails: each tool's output goes to a log
# under /tmp, printed only if that tool fails.
set -eu

out=$1
changed=false

wait_until() {
    timeout 60 sh -c "until $1; do sleep 0.2; done"
}

if [ ! -e "$out/onion/hs_ed25519_secret_key" ]; then
    : >/tmp/torrc
    tor --defaults-torrc /tmp/torrc -f /tmp/torrc --DisableNetwork 1 --SocksPort 0 \
        --DataDirectory /tmp/tor --HiddenServiceDir /tmp/onion --HiddenServicePort 80 \
        --Log 'warn stderr' >/tmp/tor.log 2>&1 &
    wait_until '[ -s /tmp/onion/hostname ]' || { cat /tmp/tor.log >&2; exit 1; }
    kill $!
    mkdir -p -m 700 "$out/onion"
    install -m 600 /tmp/onion/hs_ed25519_secret_key "$out/onion/"
    changed=true
fi

missing=
for tunnel in web gemini cgit; do
    [ -e "$out/i2p/$tunnel.dat" ] || missing="$missing $tunnel"
done
if [ -n "$missing" ]; then
    : >/tmp/i2pd.conf
    for tunnel in $missing; do
        printf '[%s]\ntype = server\nhost = 127.0.0.1\nport = 80\nkeys = %s.dat\nsignaturetype = 7\n' \
            "$tunnel" "$tunnel"
    done >/tmp/tunnels.conf
    i2pd --conf=/tmp/i2pd.conf --tunconf=/tmp/tunnels.conf --datadir=/tmp/i2pd \
        --loglevel=error --log=stdout >/tmp/i2pd.log 2>&1 &
    for tunnel in $missing; do
        wait_until "[ -s /tmp/i2pd/$tunnel.dat ]" || { cat /tmp/i2pd.log >&2; exit 1; }
    done
    kill $!
    mkdir -p -m 700 "$out/i2p"
    for tunnel in $missing; do
        install -m 600 "/tmp/i2pd/$tunnel.dat" "$out/i2p/"
    done
    changed=true
fi

if $changed; then echo changed; fi
