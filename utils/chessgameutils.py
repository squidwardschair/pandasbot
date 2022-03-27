from __future__ import annotations
import asyncio
import functools
import aiohttp
import chess
import contextlib
import discord
import re
import datetime
import time
import chess.pgn
import collections
import config
from .viewutils import button_confirm, followup_confirm
from .gameutils import get_other_player
from typing import List, Union
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import PandasBot


class ChessPlayer:
    def __init__(self, member: Union[discord.Member, None], side, timecontrol: int, bot=False, rating=None):
        self.member = member
        self.side = side
        self.timecontrol = timecontrol
        self.resignoutcome = "1-0" if side == chess.WHITE else "0-1"
        self.sidename = "White" if side == chess.WHITE else "Black"
        self.bot = bot
        self.name = f"Stockfish {rating}" if bot is True else str(member)


class ChessEmbed:
    def __init__(self, sides: List[ChessPlayer], timecontrol=None):
        self.sides = sides
        self.timecontrol = timecontrol
        self.curside = sides[0]

    async def chess_get(self, san, newfen, lastmove):
        white, black = self.sides[0], self.sides[1]
        embed = discord.Embed(title=f"Chess - {white.member} vs. {black.member}",
                              description=f"**White:** {white.member.mention} \n **Black:** {black.member.mention}", color=discord.Color.dark_gold())
        embed.add_field(
            name="Status", value=f"Ongoing - {self.curside.sidename}'s turn", inline=True)
        if self.timecontrol != None:
            embed.add_field(name="Time Control",
                            value=self.timecontrol, inline=True)
        move = chess.Move.from_uci(
            lastmove[1:]) if lastmove is not None else None
        if move is not None:
            promotionsaying = f"(Promotion to {chess.piece_name(move.promotion)})" if move.promotion != None else ""
            saying = f"{san} - {self.curside.sidename} {chess.square_name(move.from_square)}-{chess.square_name(move.to_square)} {promotionsaying}"
        embed.add_field(
            name="Last Move", value=saying if move is not None else "N/A", inline=True)
        flip = "-flip" if self.curside.side == chess.BLACK else ""
        url = f"https://chessboardimage.com/{newfen}{lastmove}{flip}.png"
        url = url.replace(" ", "%20")
        embed.set_image(url=url)
        self.curside = get_other_player(self.curside, self.sides)
        return embed


class ChessBoard(chess.Board):
    def get_push(self, move: chess.Move):
        return self.push(move)

    async def board_push(self, move: chess.Move):
        loop = asyncio.get_running_loop()
        thing = functools.partial(self.get_push, move)
        result = await loop.run_in_executor(None, thing)
        return result

    def get_pop(self):
        return self.pop()

    async def board_pop(self):
        loop = asyncio.get_running_loop()
        thing = functools.partial(self.get_pop)
        result = await loop.run_in_executor(None, thing)
        return result

    def get_outcome(self, claim_draw: bool = False):
        return self.outcome(claim_draw=claim_draw)

    async def board_outcome(self, claim_draw: bool = False):
        loop = asyncio.get_running_loop()
        thing = functools.partial(self.get_outcome, claim_draw)
        result = await loop.run_in_executor(None, thing)
        return result

    def get_gameover(self,  claim_draw: bool = False):
        return self.is_game_over(claim_draw=claim_draw)

    async def board_gameover(self, claim_draw: bool = False):
        loop = asyncio.get_running_loop()
        thing = functools.partial(self.get_gameover, claim_draw)
        result = await loop.run_in_executor(None, thing)
        return result

    def get_legal(self, move: chess.Move):
        return self.is_legal(move)

    async def board_is_legal(self, move: chess.Move):
        loop = asyncio.get_running_loop()
        thing = functools.partial(self.get_legal, move)
        result = await loop.run_in_executor(None, thing)
        return result

    def find_legal(self, from_square: chess.Square, to_square: chess.Square, promotion=None):
        return self.find_move(from_square, to_square, promotion)

    async def board_find_legal(self, from_square: chess.Square, to_square: chess.Square, promotion=None):
        loop = asyncio.get_running_loop()
        thing = functools.partial(
            self.find_legal, from_square, to_square, promotion)
        result = await loop.run_in_executor(None, thing)
        return result

    def get_san(self, san: str):
        return self.parse_san(san)

    async def board_parse_san(self, san: str):
        loop = asyncio.get_running_loop()
        thing = functools.partial(self.get_san, san)
        result = await loop.run_in_executor(None, thing)
        return result

    def move_to_san_yes(self, move: chess.Move):
        return self.san(move)

    async def board_move_to_san(self, move: chess.Move):
        loop = asyncio.get_running_loop()
        thing = functools.partial(self.move_to_san_yes, move)
        result = await loop.run_in_executor(None, thing)
        return result

    def get_fen(self):
        return self.fen()

    async def boardla_fen(self):
        loop = asyncio.get_running_loop()
        thing = functools.partial(self.get_fen)
        result = await loop.run_in_executor(None, thing)
        return result

    def get_move_stack(self):
        return self.move_stack

    async def board_move_stack(self):
        loop = asyncio.get_running_loop()
        thing = functools.partial(self.get_move_stack)
        result = await loop.run_in_executor(None, thing)
        return result

    def get_move_check(self, content: str):
        if re.search("[a-hA-H][1-8]-[a-hA-H][1-8]", content) is not None:
            movesplit = content.split("-")
            with contextlib.suppress(ValueError):
                move = self.find_move(chess.parse_square(
                    movesplit[0].lower()), chess.parse_square(movesplit[1].lower()))
                return move
        try:
            move = self.parse_san(content)
            return move
        except ValueError:
            return None

    async def move_check(self, c: str):
        loop = asyncio.get_running_loop()
        thing = functools.partial(self.get_move_check, c)
        result = await loop.run_in_executor(None, thing)
        return result


class ChessMenu(discord.ui.View):
    def __init__(self, embed: discord.Embed, players: List[ChessPlayer], turnmem: ChessPlayer, timeout: float, turntime: int, boardmsg: discord.Message, board: ChessBoard):
        super().__init__(timeout=timeout)
        print(timeout)
        self.timeout = timeout
        self.board = board
        self.embed = embed
        self.players = players
        self.playerids = [player.member.id for player in players]
        self.turnmem = turnmem
        self.turntime = turntime
        self.result = None
        self.move = None
        self.message = None
        self.drawresult = None
        self.boardmsg = boardmsg

    @discord.ui.button(label="Move", style=discord.ButtonStyle.green)
    async def open_modal(self, button: discord.Button, interaction: discord.Interaction):
        modal = Submit(self.board)
        await interaction.response.send_modal(modal)
        try:
            move = await asyncio.wait_for(modal.wait, timeout=self.timeout+0.1)
        except asyncio.TimeoutError:
            print('aaa')
            self.stop()
        if self.is_finished():
            return
        if move is False:
            print('bbbb')
            return
        self.move = move
        print('gggg')
        self.stop()

    @discord.ui.button(label='Draw', style=discord.ButtonStyle.green)
    async def draw(self, button: discord.ui.Button, interaction: discord.Interaction = discord.Interaction):
        await interaction.response.defer()
        self.drawaccepter = get_other_player(self.turnmem, self.players)
        drawresult, message = await button_confirm(self.drawaccepter.member, interaction.channel, f"{interaction.user.mention} requested a draw! {self.drawaccepter.member.mention}. __Do you accept the draw?__ You have 15 seconds or the draw will be automatically declined.", timeout=15)
        if drawresult is None:
            await message.edit("No response given, draw automatically declined.")
            await message.edit(view=None)
        elif drawresult is True:
            await message.delete()
            self.drawresult = True
            self.result = Draw(self.turnmem, self.drawaccepter)
            self.stop()
        else:
            await message.edit("The draw was declined.")
            await message.edit(view=None)

    @discord.ui.button(label='Resign', style=discord.ButtonStyle.red)
    async def Resign(self, button: discord.ui.Button, interaction: discord.Interaction = discord.Interaction):
        await interaction.response.defer()
        resignresult, message = await followup_confirm(
            interaction, 'Are you sure you wish to resign?', timeout=15
        )
        if resignresult is True:
            await message.edit(content="Resigned.", view=None)
            self.result = Resignation(
                self.turnmem, get_other_player(self.turnmem, self.players))
            self.stop()
        else:
            await message.edit(content="Resignation cancelled.", view=None)

    @discord.ui.button(label="Chess Timer", style=discord.ButtonStyle.gray, custom_id="timer")
    async def time(self, button: discord.ui.Button, interaction: discord.Interaction = discord.Interaction):
        turn, notturn = self.turnmem, get_other_player(
            self.turnmem, self.players)
        embed = discord.Embed(title=f"🕒 Chess Timer for {turn.member} vs. {notturn.member}",
                              description=f"**{turn.member}: {str(datetime.timedelta(seconds=turn.timecontrol-(round(time.time()-self.turntime))))[2:]}** \n {notturn.member}: {str(datetime.timedelta(seconds=notturn.timecontrol))[2:]}", color=discord.Color.dark_red(), timestamp=discord.utils.utcnow())
        embed.set_footer(
            text="The bolded name represents who's current move it is")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Resend Board", style=discord.ButtonStyle.gray)
    async def resend(self, button: discord.ui.Button, interaction: discord.Interaction = discord.Interaction):
        message = await interaction.response.send_message(embed=self.embed)
        self.message = message
        await self.boardmsg.delete()

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.data['custom_id'] == "timer":
            return True
        if interaction.user.id not in self.playerids:
            await interaction.response.send_message('You are not apart of this game!', ephemeral=True)
            return False
        if interaction.user.id != self.turnmem.member.id:
            await interaction.response.send_message('You can only use these buttons when its your move!', ephemeral=True)
            return False
        return True


class Submit(discord.ui.Modal):
    move = discord.ui.TextInput(
        label="Chess Move", placeholder="Make your move...", style=discord.TextStyle.short)

    def __init__(self, board: ChessBoard):
        super().__init__(title="Chess Move Menu")
        self.wait = asyncio.Future()
        self.board = board

    async def on_submit(self, interaction: discord.Interaction):
        if await self.board.move_check(self.children[0].value) is not None:
            await interaction.response.defer()
            self.wait.set_result(self.children[0].value)
        else:
            await interaction.response.send_message("Not a valid move!", ephemeral=True)
            self.wait.set_result(False)


async def get_move(board: ChessBoard, content: str):
    if re.search("[a-hA-H][1-8]-[a-hA-H][1-8]", content) is not None:
        movesplit = content.split("-")
        with contextlib.suppress(ValueError):
            move = await board.board_find_legal(chess.parse_square(movesplit[0].lower()), chess.parse_square(movesplit[1].lower()))
            return move, False
    try:
        move = await board.board_parse_san(content)
        return move, True
    except ValueError:
        return None


def board_to_pgn(board: chess.Board, white: str, black: str, result=None):
    game = chess.pgn.Game()
    moves = collections.deque()
    while board.move_stack:
        moves.append(board.pop())

    game.setup(board)
    node = game

    while moves:
        move = moves.pop()
        node = node.add_variation(move)
        board.push(move)
    beforedate = datetime.date.today().strftime('%Y-%m-%d')
    game.headers["Result"] = result or board.result(claim_draw=True)
    game.headers["White"] = white
    game.headers["Black"] = black
    game.headers["Date"] = beforedate.replace('-', '.')
    return game


async def get_pgn(session: aiohttp.ClientSession, board: chess.Board, white: str, black: str, chessresult=None):
    loop = asyncio.get_running_loop()
    thing = functools.partial(board_to_pgn, board, white, black, chessresult)
    result = await loop.run_in_executor(None, thing)
    async with session.post("https://lichess.org/api/import", headers={'Authorization': f'Bearer {config.LICHESSAPIKEY}'}, data={"pgn": result, "analyse": True}) as l:
        responsejson = await l.json()
    return responsejson['url'] if 'url' in responsejson else False


class Resignation:
    def __init__(self, resignlose: ChessPlayer, resignwin: ChessPlayer):
        self.resignwin = resignwin
        self.resignlose = resignlose
        self.outcome = resignwin.resignoutcome

    def create_saying(self):
        return f"{self.resignlose.sidename} resigned - {self.resignwin.sidename} is victorious \n *{self.outcome}* - {self.resignwin.member.mention} defeated {self.resignlose.member.mention} on resignation"


class Draw:
    def __init__(self, drawrequest: ChessPlayer, drawaccept: ChessPlayer):
        self.drawrequest = drawrequest
        self.drawaccept = drawaccept

    def create_saying(self):
        reqmem, acceptmem = self.drawrequest.member.mention, self.drawaccept.member.mention
        return f"Draw - Mutual \n *1/2-1/2* - {reqmem} requested a draw and {acceptmem} accepted"


class TimeResign(Resignation):
    def __init__(self, timewinner: ChessPlayer, timeloser: ChessPlayer, timeout=False):
        super().__init__(timewinner, timeloser)
        self.timeout = timeout

    def create_saying(self):
        winmember, losemember = self.resignwin.member, self.resignlose.member
        bfsaying1 = "went AFK on a move" if self.timeout is True else "time clocked out"
        bfsaying2 = "on move AFK" if self.timeout is True else "on time forfeiture"
        return f"{self.resignlose.sidename} {bfsaying1} - {self.resignwin.sidename} is victorious \n *{self.outcome}* - {winmember.mention} defeated {losemember.mention} {bfsaying2}"
