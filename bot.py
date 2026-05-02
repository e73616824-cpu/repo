import asyncio
import time
from datetime import datetime, timezone
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from leagues import get_leagues, get_league_by_id, get_team_by_id, search_team, search_player
from data_manager import (
    get_user_team, set_user_team, get_league_state, save_league_state,
    get_training_data, save_training_data, get_match_log,
    set_announce_channel, get_announce_channel, get_guild_data, save_guild_data
)
from match_engine import init_league, simulate_match_day
import random

TOKEN = "8618492952:AAFk5EPHoYYl9ZMJLYTDiEjrjlMyuhPkAl8"

TRAINING_TYPES = {
    'kondisyon':     {'name': 'Kondisyon Antrenmanı', 'emoji': '🏃', 'xp': 20, 'desc': 'Dayanıklılık artırır'},
    'teknik':        {'name': 'Teknik Antrenman',     'emoji': '⚽', 'xp': 25, 'desc': 'Pas ve top kontrolü'},
    'taktik':        {'name': 'Taktik Antrenman',     'emoji': '📋', 'xp': 30, 'desc': 'Savunma/hücum organizasyonu'},
    'gucantrenman':  {'name': 'Güç Antrenmanı',       'emoji': '💪', 'xp': 20, 'desc': 'Fiziksel güç ve hız'},
    'atismapraktik': {'name': 'Atış Pratiği',         'emoji': '🎯', 'xp': 28, 'desc': 'Şut isabeti'},
}
COOLDOWN_HOURS = 6

def gid(update): return str(update.effective_chat.id)
def uid(update): return str(update.effective_user.id)

async def is_admin(update, context):
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        return member.status in ('creator', 'administrator')
    except:
        return True  # özel sohbette admin say

def estimate_value(player):
    age = player.get('age', 27)
    age_factor = 1.5 if age < 23 else 1.2 if age < 27 else 1.0 if age < 30 else 0.7 if age < 33 else 0.4
    pos_mult = {'ST':1.3,'CAM':1.2,'LW':1.2,'RW':1.2,'CM':1.0,'CB':0.9,'RB':0.9,'LB':0.9,'GK':0.8}.get(player.get('position',''),1)
    raw = ((player.get('overall',70) - 60) / 30) ** 2 * 150 * age_factor * pos_mult
    return round(max(raw, 1) * 10) / 10

# ─── /start ──────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚽ <b>Futbol Botuna Hoş Geldin!</b>\n\n"
        "Bir takım seçerek başla:\n"
        "/takimsec &lt;takım adı&gt;\n\n"
        "Tüm komutlar için: /yardim",
        parse_mode='HTML'
    )

# ─── /takim ──────────────────────────────────────────────────────────────────
async def cmd_takim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    my_team_id = get_user_team(gid(update), uid(update))
    if not my_team_id:
        return await update.message.reply_text(
            "⚽ <b>Takım Seç</b>\n\n"
            "/takimsec &lt;takım adı&gt; — Takım seç\n"
            "/kadro [takım adı] — Kadro görüntüle\n"
            "/takimlar [lig_id] — Tüm takımlar\n\n"
            "<b>Örnek:</b> /takimsec Real Madrid", parse_mode='HTML')
    td = get_team_by_id(my_team_id)
    if not td:
        return await update.message.reply_text("❌ Takım bulunamadı.")
    team, league = td['team'], td['league']
    avg = round(sum(p.get('overall',70) for p in team['players']) / len(team['players'])) if team['players'] else 0
    await update.message.reply_text(
        f"{team.get('emoji','')} <b>{team['name']}</b>\n\n"
        f"🏆 Lig: {league.get('emoji','')} {league['name']}\n"
        f"🏟️ Stat: {team.get('stadium','')}\n"
        f"👔 Teknik Direktör: {team.get('manager','')}\n"
        f"👥 Kadro: {len(team['players'])} oyuncu\n"
        f"⭐ Ort. Güç: {avg} OVR\n"
        f"💰 Bütçe: €{team.get('budget',0)//1000000}M\n\n"
        f"/kadro — Kadroyu görüntüle\n/takimsec &lt;ad&gt; — Takım değiştir", parse_mode='HTML')

# ─── /takimsec ───────────────────────────────────────────────────────────────
async def cmd_takimsec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = ' '.join(context.args)
    if not query:
        return await update.message.reply_text("Kullanım: /takimsec &lt;takım adı&gt;\nÖrnek: /takimsec Manchester City", parse_mode='HTML')
    results = search_team(query)
    if not results:
        return await update.message.reply_text(f"❌ <b>{query}</b> bulunamadı. /takimlar ile listele.", parse_mode='HTML')
    team, league = results[0]['team'], results[0]['league']
    set_user_team(gid(update), uid(update), team['id'])
    await update.message.reply_text(
        f"✅ <b>Takımın Seçildi: {team.get('emoji','')} {team['name']}</b>\n\n"
        f"🏆 Lig: {league.get('emoji','')} {league['name']}\n"
        f"🏟️ Stat: {team.get('stadium','')}\n"
        f"👔 Teknik Direktör: {team.get('manager','')}\n"
        f"👥 Kadro: {len(team['players'])} oyuncu\n"
        f"💰 Bütçe: €{team.get('budget',0)//1000000}M\n\n"
        f"/antrenman ile antrenman yapmaya başla!", parse_mode='HTML')

# ─── /kadro ──────────────────────────────────────────────────────────────────
async def cmd_kadro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = ' '.join(context.args)
    if query:
        results = search_team(query)
        if not results:
            return await update.message.reply_text(f"❌ <b>{query}</b> bulunamadı.", parse_mode='HTML')
        td = results[0]
    else:
        my_id = get_user_team(gid(update), uid(update))
        if not my_id:
            return await update.message.reply_text("❌ Önce takım seç: /takimsec &lt;takım adı&gt;", parse_mode='HTML')
        td = get_team_by_id(my_id)
        if not td:
            return await update.message.reply_text("❌ Takım verisi bulunamadı.")
    team, league = td['team'], td['league']
    pos_order = ['GK','CB','RB','LB','DM','CM','CAM','RW','LW','ST']
    pos_emoji = {'GK':'🧤','CB':'🛡️','RB':'🛡️','LB':'🛡️','CM':'⚙️','CAM':'🎯','DM':'🛡️','RW':'⚡','LW':'⚡','ST':'🔥'}
    by_pos = {}
    for p in team['players']:
        by_pos.setdefault(p.get('position','?'), []).append(p)
    msg = f"{team.get('emoji','')} <b>{team['name']} — Kadro</b>\n{league.get('emoji','')} {league['name']}\n\n"
    for pos in pos_order:
        players = by_pos.get(pos, [])
        if not players: continue
        msg += f"{pos_emoji.get(pos,'⚽')} <b>{pos}</b>\n"
        for p in players:
            msg += f"  • {p['name']} ({p.get('nationality','')}) — OVR: <b>{p.get('overall',0)}</b>\n"
        msg += '\n'
    if len(msg) > 4000:
        msg = msg[:4000] + '\n<i>...(kısaltıldı)</i>'
    await update.message.reply_text(msg, parse_mode='HTML')

# ─── /takimlar ───────────────────────────────────────────────────────────────
async def cmd_takimlar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    league_id = context.args[0].lower() if context.args else None
    if not league_id:
        leagues = get_leagues()
        msg = "🌍 <b>Tüm Ligler</b>\n\n"
        for l in leagues:
            msg += f"{l.get('emoji','')} <b>{l['name']}</b> — <code>{l['id']}</code> ({len(l['teams'])} takım)\n"
        msg += "\nDetay için: /takimlar &lt;lig_id&gt;"
        return await update.message.reply_text(msg, parse_mode='HTML')
    league = get_league_by_id(league_id)
    if not league:
        return await update.message.reply_text(f"❌ <b>{league_id}</b> ligi bulunamadı.", parse_mode='HTML')
    msg = f"{league.get('emoji','')} <b>{league['name']} — Takımlar</b>\n\n"
    for t in league['teams']:
        msg += f"{t.get('emoji','')} <b>{t['name']}</b>\n   🏟️ {t.get('stadium','')} | 👔 {t.get('manager','')}\n\n"
    await update.message.reply_text(msg, parse_mode='HTML')

# ─── /antrenman ──────────────────────────────────────────────────────────────
async def cmd_antrenman(update: Update, context: ContextTypes.DEFAULT_TYPE):
    my_id = get_user_team(gid(update), uid(update))
    if not my_id:
        return await update.message.reply_text("❌ Önce takım seç: /takimsec &lt;takım adı&gt;", parse_mode='HTML')
    td = get_team_by_id(my_id)
    if not td:
        return await update.message.reply_text("❌ Takım bulunamadı.")
    team = td['team']
    sub = context.args[0].lower() if context.args else None

    if not sub:
        tr = get_training_data(gid(update), uid(update))
        cooldown_ms = COOLDOWN_HOURS * 3600
        last = tr.get('last_training', 0) if tr else 0
        can_train = (time.time() - last) > cooldown_ms
        msg = f"{team.get('emoji','')} <b>{team['name']} — Antrenman</b>\n\n"
        for key, t in TRAINING_TYPES.items():
            msg += f"{t['emoji']} /antrenman {key}\n   <i>{t['desc']}</i>\n\n"
        if can_train:
            msg += "✅ <b>Antrenman yapabilirsin!</b>"
        else:
            remaining = int((last + cooldown_ms - time.time()) / 60)
            msg += f"⏳ Sonraki antrenman: <b>{remaining} dakika</b> sonra"
        msg += f"\n📈 Toplam seans: {tr.get('total_sessions',0) if tr else 0}"
        return await update.message.reply_text(msg, parse_mode='HTML')

    tr = get_training_data(gid(update), uid(update)) or {'last_training': 0, 'total_sessions': 0, 'history': []}
    cooldown_ms = COOLDOWN_HOURS * 3600
    if (time.time() - tr.get('last_training', 0)) < cooldown_ms:
        remaining = int((tr['last_training'] + cooldown_ms - time.time()) / 60)
        return await update.message.reply_text(f"⏳ Antrenman için <b>{remaining} dakika</b> daha bekle!", parse_mode='HTML')
    if sub not in TRAINING_TYPES:
        return await update.message.reply_text("❌ Geçersiz tip. Kullanım: /antrenman", parse_mode='HTML')

    t = TRAINING_TYPES[sub]
    xp = t['xp'] + random.randint(0, 14)
    boosted = random.randint(3, 7)
    featured = random.sample(team['players'], min(3, len(team['players'])))
    featured_str = '\n'.join(f"• <b>{p['name']}</b> ({p.get('position','')})" for p in featured)
    results = ["🌟 Mükemmel antrenman! Takım harika form tutturdu.",
               "✅ İyi bir antrenman geçti. Oyuncular motivasyonlu.",
               "📈 Verimli çalışma. Bazı oyuncular dikkat çekti.",
               "⚽ Solid bir antrenman. Taktikler oturdu.",
               "💪 Fiziksel antrenman tamamlandı. Takım güçlendi."]

    tr['last_training'] = time.time()
    tr['total_sessions'] = tr.get('total_sessions', 0) + 1
    tr.setdefault('history', []).insert(0, {'type': sub, 'xp': xp, 'date': int(time.time())})
    tr['history'] = tr['history'][:20]
    save_training_data(gid(update), uid(update), tr)

    await update.message.reply_text(
        f"{t['emoji']} <b>{t['name']} Tamamlandı!</b>\n\n"
        f"{random.choice(results)}\n\n"
        f"⭐ XP: <b>+{xp} XP</b>\n"
        f"👥 Etkilenen: <b>{boosted} oyuncu</b>\n\n"
        f"🌟 <b>Öne Çıkanlar:</b>\n{featured_str}\n\n"
        f"⏳ Sonraki antrenman: {COOLDOWN_HOURS} saat sonra", parse_mode='HTML')

# ─── /transfer ───────────────────────────────────────────────────────────────
async def cmd_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💰 <b>Transfer Sistemi</b>\n\n"
        "/transferara &lt;oyuncu adı&gt; — Oyuncu ara\n"
        "/oyuncu &lt;oyuncu adı&gt; — Oyuncu detayı\n"
        "/pazar — Günlük transfer pazarı\n\n"
        "<b>Örnekler:</b>\n"
        "/transferara Haaland\n/oyuncu Vinicius", parse_mode='HTML')

async def cmd_transferara(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = ' '.join(context.args)
    if not query:
        return await update.message.reply_text("Kullanım: /transferara &lt;oyuncu adı&gt;", parse_mode='HTML')
    results = search_player(query)
    if not results:
        return await update.message.reply_text(f"❌ <b>{query}</b> için sonuç bulunamadı.", parse_mode='HTML')
    shown = results[:10]
    msg = f"🔍 <b>Transfer Araması: \"{query}\"</b>\n\n"
    for r in shown:
        p = r['player']
        val = estimate_value(p)
        msg += f"<b>{p['name']}</b> | {p.get('position','')} | OVR: {p.get('overall',0)} | {r['team'].get('emoji','')} {r['team']['shortName']} | 💰 €{val}M\n"
    if len(results) > 10:
        msg += f"\n<i>{len(results)} sonuç bulundu, ilk 10 gösteriliyor</i>"
    await update.message.reply_text(msg, parse_mode='HTML')

async def cmd_oyuncu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = ' '.join(context.args)
    if not query:
        return await update.message.reply_text("Kullanım: /oyuncu &lt;oyuncu adı&gt;", parse_mode='HTML')
    results = search_player(query)
    if not results:
        return await update.message.reply_text(f"❌ <b>{query}</b> bulunamadı.", parse_mode='HTML')
    r = results[0]; p = r['player']; team = r['team']; league = r['league']
    val = estimate_value(p)
    await update.message.reply_text(
        f"👤 <b>{p['name']}</b>\n\n"
        f"🏃 Mevki: <b>{p.get('position','')}</b>\n"
        f"🌍 Milliyet: {p.get('nationality','')}\n"
        f"🎂 Yaş: {p.get('age','')}\n"
        f"⭐ OVR: <b>{p.get('overall',0)}</b>\n"
        f"💰 Tahmini Değer: €{val}M\n"
        f"💵 Maaş: £{p.get('wage',0)//1000}K/hafta\n"
        f"🏟️ Mevcut Takım: {team.get('emoji','')} {team['name']}\n"
        f"🏆 Lig: {league.get('emoji','')} {league['name']}", parse_mode='HTML')

async def cmd_pazar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_players = []
    for league in get_leagues():
        for team in league['teams']:
            for player in team.get('players', []):
                if 75 <= player.get('overall', 0) <= 85:
                    all_players.append({'player': player, 'team': team, 'league': league, 'value': estimate_value(player)})
    market = random.sample(all_players, min(8, len(all_players)))
    msg = "💰 <b>Transfer Pazarı — Günlük Teklifler</b>\n\n"
    for item in market:
        p = item['player']
        msg += f"<b>{p['name']}</b> ({p.get('position','')}) OVR: {p.get('overall',0)}\n"
        msg += f"  {item['team'].get('emoji','')} {item['team']['shortName']} | 💰 €{item['value']}M | 🌍 {p.get('nationality','')}\n\n"
    msg += "<i>Detay için: /oyuncu &lt;isim&gt;</i>"
    await update.message.reply_text(msg, parse_mode='HTML')

# ─── /puan ───────────────────────────────────────────────────────────────────
async def cmd_puan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    league_id = context.args[0].lower() if context.args else None
    if not league_id:
        leagues = get_leagues()
        msg = "📊 <b>Puan Durumu</b>\n\nLig belirtin:\n\n"
        for l in leagues:
            msg += f"{l.get('emoji','')} <code>/puan {l['id']}</code> — {l['name']}\n"
        return await update.message.reply_text(msg, parse_mode='HTML')
    state = get_league_state(gid(update), league_id)
    if not state:
        return await update.message.reply_text(f"❌ <b>{league_id}</b> ligi başlatılmamış.\n/ligbaslat {league_id}", parse_mode='HTML')
    sorted_s = sorted(state['standings'].values(), key=lambda t: (-t['points'], -t['goal_diff']))
    league_data = get_league_by_id(league_id)
    medals = ['🥇','🥈','🥉']
    msg = f"{league_data.get('emoji','🏆')} <b>{state['league_name']} — Puan Durumu</b>\n📅 Hafta {state['current_round']}/{state['total_rounds']}\n\n"
    for i, t in enumerate(sorted_s):
        pos = medals[i] if i < 3 else f"{i+1}."
        gd = f"+{t['goal_diff']}" if t['goal_diff'] >= 0 else str(t['goal_diff'])
        msg += f"{pos} <b>{t['team_name']}</b> — <b>{t['points']}P</b>\n"
        msg += f"    {t['played']}O {t['won']}G {t['drawn']}B {t['lost']}M | {t['goals_for']}:{t['goals_against']} ({gd})\n"
    await update.message.reply_text(msg, parse_mode='HTML')

# ─── /sonuclar ───────────────────────────────────────────────────────────────
async def cmd_sonuclar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log = get_match_log(gid(update), 10)
    if not log:
        return await update.message.reply_text("❌ Henüz hiç maç oynanmadı.")
    msg = "📋 <b>Son Maç Sonuçları</b>\n\n"
    for m in log:
        date = datetime.fromtimestamp(m.get('timestamp',0)).strftime('%d.%m.%Y')
        hg, ag = m.get('home_goals',0), m.get('away_goals',0)
        arrow = '›' if hg > ag else '‹' if ag > hg else '='
        msg += f"<b>{m['home_team']} {hg}–{ag} {m['away_team']}</b> {arrow}  <i>{date}</i>\n"
    await update.message.reply_text(msg, parse_mode='HTML')

# ─── /fikstür ────────────────────────────────────────────────────────────────
async def cmd_fikstür(update: Update, context: ContextTypes.DEFAULT_TYPE):
    league_id = context.args[0].lower() if context.args else None
    if not league_id:
        leagues = get_leagues()
        msg = "📅 <b>Fikstür</b>\n\nLig belirtin:\n\n"
        for l in leagues:
            msg += f"{l.get('emoji','')} <code>/fikstür {l['id']}</code> — {l['name']}\n"
        return await update.message.reply_text(msg, parse_mode='HTML')
    state = get_league_state(gid(update), league_id)
    if not state:
        return await update.message.reply_text(f"❌ <b>{league_id}</b> ligi başlatılmamış.", parse_mode='HTML')
    league_data = get_league_by_id(league_id)
    next_round = state['current_round'] + 1
    show_rounds = state['fixtures'][next_round-1:next_round+2]
    if not show_rounds:
        return await update.message.reply_text("🏁 Fikstür tamamlandı.")
    msg = f"{league_data.get('emoji','')} <b>{state['league_name']} — Fikstür</b>\nMevcut Hafta: {state['current_round']}/{state['total_rounds']}\n\n"
    for rnd in show_rounds:
        label = " (Sonraki)" if rnd['round'] == next_round else ""
        msg += f"<b>📅 Hafta {rnd['round']}{label}</b>\n"
        for match in rnd['matches']:
            ht = next((t for t in league_data['teams'] if t['id'] == match['home']), None)
            at = next((t for t in league_data['teams'] if t['id'] == match['away']), None)
            if ht and at:
                msg += f"  {ht.get('emoji','')} {ht['shortName']} vs {at['shortName']} {at.get('emoji','')}\n"
        msg += '\n'
    await update.message.reply_text(msg, parse_mode='HTML')

# ─── Admin komutları ─────────────────────────────────────────────────────────
async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("❌ Yönetici yetkisi gerekli!")
    await update.message.reply_text(
        "⚙️ <b>Admin Komutları</b>\n\n"
        "/ligbaslat &lt;lig_id&gt; — Lig başlat\n"
        "/ligdurdur &lt;lig_id&gt; — Ligi durdur\n"
        "/ligsifirla &lt;lig_id&gt; — Ligi sıfırla\n"
        "/ligler — Aktif ligleri göster\n"
        "/adminpuan &lt;lig_id&gt; — Puan durumu\n"
        "/simule — Manuel maç simülasyonu\n"
        "/kanal — Bu kanalı duyuru kanalı yap\n\n"
        "<b>Lig ID'leri:</b>\n"
        "<code>premier_league</code> | <code>la_liga</code> | <code>bundesliga</code>\n"
        "<code>serie_a</code> | <code>ligue_1</code> | <code>eredivisie</code> | <code>primeira_liga</code>",
        parse_mode='HTML')

async def cmd_ligbaslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("❌ Yönetici yetkisi gerekli!")
    league_id = context.args[0].lower() if context.args else None
    if not league_id:
        leagues = get_leagues()
        msg = "📋 <b>Mevcut Ligler:</b>\n\n"
        for l in leagues:
            msg += f"{l.get('emoji','')} <code>{l['id']}</code> — {l['name']}\n"
        msg += "\nKullanım: /ligbaslat &lt;lig_id&gt;"
        return await update.message.reply_text(msg, parse_mode='HTML')
    existing = get_league_state(gid(update), league_id)
    if existing and existing.get('status') == 'active':
        return await update.message.reply_text(
            f"⚠️ <b>{existing['league_name']}</b> zaten aktif!\nDurdurmak için: /ligdurdur {league_id}", parse_mode='HTML')
    try:
        state = init_league(gid(update), league_id)
        league_data = get_league_by_id(league_id)
        team_list = '\n'.join(f"{t.get('emoji','')} {t['name']}" for t in league_data['teams'])
        await update.message.reply_text(
            f"✅ <b>{league_data.get('emoji','')} {state['league_name']} Başlatıldı!</b>\n\n"
            f"🏟️ Takım Sayısı: {len(league_data['teams'])} takım\n"
            f"📅 Toplam Hafta: {state['total_rounds']} hafta\n"
            f"⚡ Otomatik Maçlar: Her gün 18:00 ve 20:00 (TR)\n\n"
            f"<b>Takımlar:</b>\n{team_list}\n\n"
            f"📢 Duyuru için: /kanal", parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ Hata: {e}")

async def cmd_ligdurdur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("❌ Yönetici yetkisi gerekli!")
    league_id = context.args[0].lower() if context.args else None
    if not league_id:
        return await update.message.reply_text("Kullanım: /ligdurdur &lt;lig_id&gt;", parse_mode='HTML')
    state = get_league_state(gid(update), league_id)
    if not state:
        return await update.message.reply_text("❌ Bu lig bulunamadı.")
    state['status'] = 'stopped'
    save_league_state(gid(update), league_id, state)
    await update.message.reply_text(f"⏹️ <b>{state['league_name']}</b> durduruldu.", parse_mode='HTML')

async def cmd_ligsifirla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("❌ Yönetici yetkisi gerekli!")
    league_id = context.args[0].lower() if context.args else None
    if not league_id:
        return await update.message.reply_text("Kullanım: /ligsifirla &lt;lig_id&gt;", parse_mode='HTML')
    data = get_guild_data(gid(update))
    if 'leagues' in data and league_id in data['leagues']:
        del data['leagues'][league_id]
        save_guild_data(gid(update), data)
        return await update.message.reply_text(f"🔄 <b>{league_id}</b> ligi sıfırlandı.", parse_mode='HTML')
    await update.message.reply_text("❌ Lig bulunamadı.")

async def cmd_ligler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("❌ Yönetici yetkisi gerekli!")
    data = get_guild_data(gid(update))
    active = list(data.get('leagues', {}).values())
    if not active:
        leagues = get_leagues()
        msg = "📋 <b>Başlatılabilir Ligler:</b>\n\n"
        for l in leagues:
            msg += f"{l.get('emoji','')} <code>{l['id']}</code> — {l['name']} ({len(l['teams'])} takım)\n"
        msg += "\n/ligbaslat &lt;id&gt; ile başlatabilirsin."
        return await update.message.reply_text(msg, parse_mode='HTML')
    msg = "🏆 <b>Aktif Ligler</b>\n\n"
    for s in active:
        emoji = '🟢' if s['status'] == 'active' else '🔴' if s['status'] == 'stopped' else '🏁'
        msg += f"{emoji} <b>{s['league_name']}</b>\n   Durum: {s['status']} | Hafta: {s['current_round']}/{s['total_rounds']}\n\n"
    await update.message.reply_text(msg, parse_mode='HTML')

async def cmd_adminpuan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("❌ Yönetici yetkisi gerekli!")
    league_id = context.args[0].lower() if context.args else None
    if not league_id:
        return await update.message.reply_text("Kullanım: /adminpuan &lt;lig_id&gt;", parse_mode='HTML')
    state = get_league_state(gid(update), league_id)
    if not state:
        return await update.message.reply_text("❌ Bu lig bulunamadı.")
    sorted_s = sorted(state['standings'].values(), key=lambda t: (-t['points'], -t['goal_diff']))
    medals = ['🥇','🥈','🥉']
    msg = f"📊 <b>{state['league_name']} — Puan Durumu</b>\nHafta {state['current_round']}/{state['total_rounds']}\n\n"
    for i, t in enumerate(sorted_s):
        pos = medals[i] if i < 3 else f"{i+1}."
        gd = f"+{t['goal_diff']}" if t['goal_diff'] >= 0 else str(t['goal_diff'])
        msg += f"{pos} <b>{t['team_name']}</b> — {t['points']}P | {t['played']}O {t['won']}G {t['drawn']}B {t['lost']}M | {t['goals_for']}:{t['goals_against']} ({gd})\n"
    await update.message.reply_text(msg, parse_mode='HTML')

async def cmd_simule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("❌ Yönetici yetkisi gerekli!")
    await update.message.reply_text("⏳ Maç simülasyonu başlıyor...")
    app = context.application
    try:
        await simulate_match_day(app)
    except Exception as e:
        await update.message.reply_text(f"❌ Hata: {e}")

async def cmd_kanal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("❌ Yönetici yetkisi gerekli!")
    set_announce_channel(gid(update), str(update.effective_chat.id))
    await update.message.reply_text("✅ Bu kanal/grup duyuru kanalı olarak ayarlandı!\nMaç sonuçları buraya gönderilecek.")

# ─── /yardim ─────────────────────────────────────────────────────────────────
async def cmd_yardim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚽ <b>Futbol Botu — Komutlar</b>\n\n"
        "👤 <b>Takım</b>\n"
        "/takim — Takım bilgisi\n"
        "/takimsec &lt;takım adı&gt; — Takım seç\n"
        "/kadro [takım adı] — Kadroyu görüntüle\n"
        "/takimlar [lig_id] — Tüm takımlar\n\n"
        "🏋️ <b>Antrenman</b>\n"
        "/antrenman — Antrenman listesi\n"
        "/antrenman kondisyon | teknik | taktik | gucantrenman | atismapraktik\n\n"
        "💰 <b>Transfer</b>\n"
        "/transfer — Transfer menüsü\n"
        "/transferara &lt;oyuncu&gt; — Oyuncu ara\n"
        "/oyuncu &lt;oyuncu&gt; — Oyuncu detayı\n"
        "/pazar — Günlük transfer pazarı\n\n"
        "📊 <b>Lig &amp; Sonuçlar</b>\n"
        "/puan &lt;lig_id&gt; — Puan durumu\n"
        "/sonuclar — Son maç sonuçları\n"
        "/fikstür &lt;lig_id&gt; — Yaklaşan maçlar\n\n"
        "⚙️ <b>Admin</b>\n"
        "/ligbaslat &lt;lig_id&gt; — Lig başlat\n"
        "/ligdurdur &lt;lig_id&gt; — Ligi durdur\n"
        "/ligsifirla &lt;lig_id&gt; — Sıfırla\n"
        "/ligler — Aktif ligler\n"
        "/adminpuan &lt;lig_id&gt; — Puan tablosu\n"
        "/simule — Manuel maç simülasyonu\n"
        "/kanal — Duyuru kanalı ayarla\n\n"
        "🌍 <b>Lig ID'leri:</b>\n"
        "<code>premier_league</code> <code>la_liga</code> <code>bundesliga</code>\n"
        "<code>serie_a</code> <code>ligue_1</code> <code>eredivisie</code> <code>primeira_liga</code>\n\n"
        "<i>⚡ Maçlar her gün 18:00 ve 20:00'de otomatik oynanır!</i>",
        parse_mode='HTML')

# ─── Zamanlayıcı ─────────────────────────────────────────────────────────────
async def scheduled_match(context: ContextTypes.DEFAULT_TYPE):
    print("⚽ Otomatik maç simülasyonu başlıyor...")
    await simulate_match_day(context.application)

# ─── Ana fonksiyon ────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(TOKEN).build()

    # Komutları kaydet
    commands = [
        ('start', cmd_start), ('takim', cmd_takim), ('takimsec', cmd_takimsec),
        ('kadro', cmd_kadro), ('takimlar', cmd_takimlar),
        ('antrenman', cmd_antrenman),
        ('transfer', cmd_transfer), ('transferara', cmd_transferara),
        ('oyuncu', cmd_oyuncu), ('pazar', cmd_pazar),
        ('puan', cmd_puan), ('sonuclar', cmd_sonuclar),
        ('fikstür', cmd_fikstür), ('fikstúr', cmd_fikstür),
        ('admin', cmd_admin), ('ligbaslat', cmd_ligbaslat),
        ('ligdurdur', cmd_ligdurdur), ('ligsifirla', cmd_ligsifirla),
        ('ligler', cmd_ligler), ('adminpuan', cmd_adminpuan),
        ('simule', cmd_simule), ('kanal', cmd_kanal),
        ('yardim', cmd_yardim),
    ]
    for name, handler in commands:
        app.add_handler(CommandHandler(name, handler))

    # Zamanlanmış maçlar: 18:00 ve 20:00 TR (UTC+3 = 15:00 ve 17:00 UTC)
    job_queue = app.job_queue
    job_queue.run_daily(scheduled_match, time=__import__('datetime').time(15, 0, tzinfo=__import__('datetime').timezone.utc))
    job_queue.run_daily(scheduled_match, time=__import__('datetime').time(17, 0, tzinfo=__import__('datetime').timezone.utc))

    print("✅ Bot başlatıldı!")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
