from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ServiceRule:
    list_general: tuple[str, ...] = field(default_factory=tuple)
    list_exclude: tuple[str, ...] = field(default_factory=tuple)
    list_google: tuple[str, ...] = field(default_factory=tuple)
    ipset_all: tuple[str, ...] = field(default_factory=tuple)
    ipset_exclude: tuple[str, ...] = field(default_factory=tuple)
    hosts: tuple[str, ...] = field(default_factory=tuple)
    extra_lists: tuple[tuple[str, tuple[str, ...]], ...] = field(default_factory=tuple)
    extra_list_files: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    winws_args: tuple[str, ...] = field(default_factory=tuple)
    test_targets: tuple[tuple[str, str], ...] = field(default_factory=tuple)


SERVICE_RULES: dict[str, ServiceRule] = {
    "cloudflare": ServiceRule(
        list_general=(
            "cloudflare.com",
            "cloudflare-dns.com",
            "cloudflare-ech.com",
            "cloudflare-gateway.com",
            "cloudflareinsights.com",
            "cloudflarestream.com",
            "cloudflarewarp.com",
            "one.one.one.one",
        ),
        ipset_all=(
            "1.1.1.0/24",
            "1.0.0.0/24",
            "104.16.0.0/13",
            "104.24.0.0/14",
            "108.162.192.0/18",
            "131.0.72.0/22",
            "141.101.64.0/18",
            "162.158.0.0/15",
            "172.64.0.0/13",
            "173.245.48.0/20",
            "188.114.96.0/20",
            "190.93.240.0/20",
            "197.234.240.0/22",
            "198.41.128.0/17",
        ),
        test_targets=(("Cloudflare", "https://www.cloudflare.com"), ("Cloudflare DNS", "PING:1.1.1.1")),
    ),
    "discord": ServiceRule(
        list_general=(
            "discord.com",
            "discord.gg",
            "discord.media",
            "discordapp.com",
            "discordapp.net",
            "discordcdn.com",
            "discordstatus.com",
            "gateway.discord.gg",
        ),
        test_targets=(("Discord", "https://discord.com"), ("Discord Gateway", "https://gateway.discord.gg")),
    ),
    "youtube": ServiceRule(
        list_general=(
            "googlevideo.com",
            "gvt1.com",
            "video.google.com",
            "withyoutube.com",
            "youtu.be",
            "youtube.com",
            "youtube-nocookie.com",
            "youtubei.googleapis.com",
            "ytimg.com",
        ),
        list_google=("googlevideo.com", "gvt1.com", "youtube.com", "youtu.be", "ytimg.com"),
        test_targets=(("YouTube", "https://www.youtube.com"), ("YouTube 204", "https://www.youtube.com/generate_204")),
    ),
    "telegram-desktop": ServiceRule(),
    "clouds": ServiceRule(
        list_general=(
            "amazonaws.com",
            "awsstatic.com",
            "cloudfront.net",
            "b-cdn.net",
            "bunny.net",
            "bunnycdn.com",
            "ovh.net",
            "ovhcloud.com",
            "akamaized.net",
            "edgekey.net",
            "edgesuite.net",
            "fastly.net",
            "fastlylb.net",
            "fastly-edge.com",
            "cdn77.com",
            "cdn77.org",
        ),
        ipset_exclude=(
            "0.0.0.0/8",
            "10.0.0.0/8",
            "127.0.0.0/8",
            "192.168.0.0/16",
            "185.71.66.225",
            "185.71.67.221",
        ),
        extra_list_files=(("ipset-all.txt", "sample_data/default_services/clouds/lists/ipset-all.txt"),),
        test_targets=(
            ("Amazon AWS", "https://aws.amazon.com"),
            ("Bunny CDN", "https://bunny.net"),
            ("OVHcloud", "https://www.ovhcloud.com"),
        ),
    ),
    "roblox": ServiceRule(
        list_general=(
            "roblox.com",
            "rbxcdn.com",
            "robloxcdn.com",
            "rblx.com",
            "robloxapp.com",
            "gamejoin.roblox.com",
            "setup.rbxcdn.com",
            "setup.roblox.com",
            "contentdelivery.roblox.com",
        ),
        ipset_all=(
            "103.140.28.0/23",
            "128.116.0.0/17",
            "141.193.3.0/24",
            "205.201.62.0/24",
        ),
        hosts=(
            "23.47.124.101 tr.rbxcdn.com",
            "23.47.124.78 tr.rbxcdn.com",
        ),
        test_targets=(("Roblox", "https://www.roblox.com"), ("Roblox CDN", "https://setup.rbxcdn.com")),
    ),
    "tiktok": ServiceRule(
        list_general=("tiktok.com", "tiktokcdn.com", "tiktokv.com", "byteoversea.com", "ibytedtos.com", "muscdn.com", "bytecdn.cn"),
        test_targets=(("TikTok", "https://www.tiktok.com"),),
    ),
    "instagram": ServiceRule(
        list_general=("instagram.com", "cdninstagram.com", "static.cdninstagram.com", "ig.me", "threads.net"),
        test_targets=(("Instagram", "https://www.instagram.com"),),
    ),
    "epic-games": ServiceRule(
        list_general=("epicgames.com", "epicgames.dev", "epicgamescdn.com", "unrealengine.com", "akamaized.net", "cloudfront.net"),
        list_exclude=("easy.ac", "easyanticheat.net", "easyanticheat.com"),
        test_targets=(("Epic Games", "https://www.epicgames.com"),),
    ),
    "battle-net": ServiceRule(
        list_general=("battle.net", "blizzard.com", "blizzard.net", "blz-contentstack.com", "blzddist1-a.akamaihd.net"),
        test_targets=(("Battle.net", "https://www.battle.net"),),
    ),
    "spotify": ServiceRule(
        list_general=(
            "spotify.com",
            "scdn.co",
            "spotifycdn.com",
            "open.spotify.com",
            "api.spotify.com",
            "accounts.spotify.com",
            "gew1-spclient.spotify.com",
            "login5.spotify.com",
            "spclient.wg.spotify.com",
            "api-partner.spotify.com",
            "appresolve.spotify.com",
        ),
        test_targets=(("Spotify", "https://open.spotify.com"),),
    ),
    "reddit": ServiceRule(
        list_general=("reddit.com", "redd.it", "redditmedia.com", "redditstatic.com", "redditinc.com"),
        test_targets=(("Reddit", "https://www.reddit.com"),),
    ),
    "x-twitter": ServiceRule(
        list_general=("x.com", "api.x.com", "twitter.com", "api.tweetdeck.com", "twimg.com", "pbs.twimg.com", "video.twimg.com", "t.co"),
        test_targets=(("X", "https://x.com"),),
    ),
    "github": ServiceRule(
        list_general=(
            "github.com",
            "githubusercontent.com",
            "raw.githubusercontent.com",
            "githubassets.com",
            "github.io",
            "objects.githubusercontent.com",
            "codeload.github.com",
        ),
        test_targets=(("GitHub", "https://github.com"), ("GitHub Raw", "https://raw.githubusercontent.com")),
    ),
    "riot-games": ServiceRule(
        list_general=("riotgames.com", "riotcdn.net", "pvp.net", "auth.riotgames.com", "clientconfig.rpg.riotgames.com"),
        test_targets=(("Riot Games", "https://www.riotgames.com"),),
    ),
    "league-of-legends": ServiceRule(
        list_general=("leagueoflegends.com", "lolstatic.com", "lolesports.com", "riotcdn.net", "pvp.net"),
        ipset_all=("3.64.0.0/12", "18.156.0.0/14", "18.165.180.0/22", "35.156.0.0/14", "44.224.0.0/11", "99.83.128.0/20"),
        extra_lists=(("ipset-lol.txt", ("3.64.0.0/12", "18.156.0.0/14", "18.165.180.0/22", "35.156.0.0/14", "44.224.0.0/11", "99.83.128.0/20")),),
        winws_args=("--new", "--filter-tcp=2099", "--ipset={lists}/ipset-lol.txt", "--dpi-desync=syndata"),
        test_targets=(("League of Legends", "https://www.leagueoflegends.com"),),
    ),
    "figma": ServiceRule(
        list_general=("figma.com", "www.figma.com", "figma.net", "figma-alpha-api.s3.us-west-2.amazonaws.com"),
        ipset_all=("18.66.0.0/16", "52.222.0.0/15", "54.230.0.0/16", "108.138.0.0/15", "143.204.0.0/16", "199.232.0.0/16", "205.251.192.0/18"),
        test_targets=(("Figma", "https://www.figma.com"),),
    ),
    "netflix": ServiceRule(
        list_general=("netflix.com", "nflxvideo.net", "nflximg.net", "nflxso.net", "nflxext.com", "fast.com"),
        test_targets=(("Netflix", "https://www.netflix.com"),),
    ),
    "facebook": ServiceRule(
        list_general=("facebook.com", "fbcdn.net", "fbsbx.com", "accountkit.com", "facebookauth.com", "facebook.net", "fb.com", "fb.me"),
        test_targets=(("Facebook", "https://www.facebook.com"),),
    ),
    "wplace": ServiceRule(
        list_general=("wplace.live",),
        test_targets=(("WPlace", "https://wplace.live"),),
    ),
    "facetime": ServiceRule(
        list_general=(
            "apple.com",
            "icloud.com",
            "appleid.apple.com",
            "gs.apple.com",
            "gateway.push.apple.com",
            "*.push.apple.com",
            "init-p01md.push.apple.com",
            "init-p01st.push.apple.com",
            "apple-cloudkit.com",
            "cdn-apple.com",
            "apple-dns.net",
            "apple.news",
            "digicert.com",
        ),
        ipset_all=(
            "17.0.0.0/8",
            "63.92.224.0/19",
            "65.199.176.0/20",
            "139.178.0.0/16",
            "144.178.0.0/16",
            "192.35.50.0/24",
            "192.35.52.0/24",
            "192.35.54.0/24",
            "192.35.56.0/24",
            "192.35.58.0/24",
        ),
        test_targets=(("FaceTime", "https://facetime.apple.com"),),
    ),
    "ai": ServiceRule(),
    "dnd": ServiceRule(
        list_general=(
            "dndbeyond.com",
            "www.dndbeyond.com",
            "auth.dndbeyond.com",
            "media.dndbeyond.com",
            "images.dndbeyond.com",
            "api.dndbeyond.com",
            "dnd.wizards.com",
            "dndstore.wizards.com",
            "accounts.wizards.com",
            "roll20.net",
            "www.roll20.net",
            "app.roll20.net",
            "marketplace.roll20.net",
            "owlbear.rodeo",
            "www.owlbear.rodeo",
            "app.owlbear.rodeo",
            "foundryvtt.com",
            "www.foundryvtt.com",
            "forge-vtt.com",
            "eu.forge-vtt.com",
            "us.forge-vtt.com",
            "inkarnate.com",
            "wonderdraft.net",
            "koboldplus.club",
        ),
        test_targets=(
            ("D&D Beyond", "https://www.dndbeyond.com"),
            ("Roll20", "https://roll20.net"),
            ("Foundry VTT", "https://foundryvtt.com"),
        ),
    ),
}
