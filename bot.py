#!/usr/bin/env python3
import discord
from discord.ext import commands, tasks
import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
import json

# ============================================
# BOT DISCORD - MONITORAMENTO INSTAGRAM
# ============================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Dicionário para guardar monitoramentos
monitoramentos = {}

# ============================================
# FUNÇÕES DE VERIFICAÇÃO
# ============================================

def verificar_instagram(username):
    """Verifica status de uma conta Instagram"""
    try:
        url = f"https://www.instagram.com/{username}/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 404:
            return {'status': 'banido', 'encontrado': False}
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Tentar extrair dados
            try:
                scripts = soup.find_all('script', {'type': 'application/ld+json'})
                for script in scripts:
                    data = json.loads(script.string)
                    if 'author' in data:
                        return {
                            'status': 'ativo',
                            'encontrado': True,
                            'seguidores': data.get('interactionStatistic', [{}])[0].get('userInteractionCount', 0),
                            'posts': len(data.get('image', [])),
                            'bio': data.get('description', ''),
                            'verificado': data.get('verified', False),
                            'foto': data.get('image', [None])[0] if data.get('image') else None
                        }
            except:
                pass
            
            return {'status': 'ativo', 'encontrado': True}
        
        return {'status': 'inativo', 'encontrado': True}
        
    except:
        return {'status': 'inativo', 'encontrado': True}

# ============================================
# EVENTOS DO BOT
# ============================================

@bot.event
async def on_ready():
    print(f'✅ Bot conectado como {bot.user}')
    print(f'📊 Monitorando {len(monitoramentos)} conta(s)')
    verificar_contas.start()

# ============================================
# COMANDO !unban
# ============================================

@bot.command(name='unban')
async def unban(ctx, username: str):
    """Comando para monitorar conta Instagram"""
    
    # Remover @ se tiver
    username = username.replace('@', '').strip()
    
    if not username:
        await ctx.send("❌ Username inválido!")
        return
    
    # Verificar se já está monitorando
    if username in monitoramentos:
        await ctx.send(f"⚠️ @{username} já está sendo monitorado!")
        return
    
    # Criar embed de confirmação
    embed = discord.Embed(
        title="📊 Monitoring Status",
        description=f"User @{username} is being monitored!",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    embed.set_footer(text="Instagram Monitor Bot")
    
    await ctx.send(embed=embed)
    
    # Adicionar ao monitoramento
    monitoramentos[username] = {
        'canal_id': ctx.channel.id,
        'status_anterior': None,
        'tempo_inicio': datetime.now(),
        'servidor_id': ctx.guild.id
    }
    
    print(f"🔍 Monitorando @{username}")

# ============================================
# TAREFA DE VERIFICAÇÃO
# ============================================

@tasks.loop(seconds=1)
async def verificar_contas():
    """Verifica contas a cada 1 segundo"""
    
    if not monitoramentos:
        return
    
    contas_remover = []
    
    for username, dados in monitoramentos.items():
        try:
            # Verificar status
            resultado = verificar_instagram(username)
            status_atual = resultado['status']
            
            # Se mudou de status
            if dados['status_anterior'] is None or dados['status_anterior'] != status_atual:
                
                # Obter canal
                try:
                    canal = bot.get_channel(dados['canal_id'])
                    if not canal:
                        contas_remover.append(username)
                        continue
                    
                    # Calcular tempo decorrido
                    tempo_decorrido = (datetime.now() - dados['tempo_inicio']).total_seconds()
                    horas = int(tempo_decorrido // 3600)
                    minutos = int((tempo_decorrido % 3600) // 60)
                    segundos = int(tempo_decorrido % 60)
                    
                    # Criar embed
                    if status_atual == 'ativo':
                        cor = discord.Color.green()
                        titulo = "✅ Account Recovered"
                        descricao = f"@{username} voltou ATIVO!"
                    elif status_atual == 'banido':
                        cor = discord.Color.red()
                        titulo = "🚫 Account Banned"
                        descricao = f"@{username} foi BANIDO!"
                    else:
                        cor = discord.Color.yellow()
                        titulo = "⏳ Account Offline"
                        descricao = f"@{username} está OFFLINE"
                    
                    embed = discord.Embed(
                        title=titulo,
                        description=descricao,
                        color=cor,
                        timestamp=datetime.now()
                    )
                    
                    embed.add_field(name="👤 Usuário", value=f"@{username}", inline=True)
                    embed.add_field(name="👥 Seguidores", value=f"{resultado.get('seguidores', 0):,}", inline=True)
                    embed.add_field(name="📸 Posts", value=str(resultado.get('posts', 0)), inline=True)
                    embed.add_field(name="✓ Verificado", value="Sim" if resultado.get('verificado') else "Não", inline=True)
                    embed.add_field(
                        name="⏱️ Tempo Decorrido",
                        value=f"{horas} horas, {minutos} minutos, {segundos} segundos",
                        inline=False
                    )
                    embed.add_field(name="📝 Bio", value=resultado.get('bio', 'Sem bio')[:100], inline=False)
                    
                    if resultado.get('foto'):
                        embed.set_thumbnail(url=resultado['foto'])
                    
                    embed.set_footer(text="Instagram Monitor Bot")
                    
                    await canal.send(embed=embed)
                    
                    # Atualizar status
                    dados['status_anterior'] = status_atual
                    
                except Exception as e:
                    print(f"❌ Erro ao enviar mensagem: {str(e)}")
                    contas_remover.append(username)
        
        except Exception as e:
            print(f"❌ Erro ao verificar @{username}: {str(e)}")
    
    # Remover contas com erro
    for username in contas_remover:
        if username in monitoramentos:
            del monitoramentos[username]
            print(f"❌ Removido @{username} do monitoramento")

# ============================================
# INICIAR BOT
# ============================================

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    
    if not token:
        print("❌ ERRO: DISCORD_TOKEN não configurado!")
        print("Configure a variável de ambiente DISCORD_TOKEN")
        exit()
    
    try:
        bot.run(token)
    except Exception as e:
        print(f"❌ Erro ao iniciar bot: {str(e)}")
