from __future__ import annotations
import asyncio
from shutil import move
import chess
import discord
import datetime
import time
import chess.pgn
from discord.ext import commands, tasks
import random
from utils.gameutils import request_game, get_other_player
from utils.viewutils import list_select, list_buttons
from utils.chessgameutils import ChessMenu, ChessPlayer, Draw, Resignation, TimeResign, ChessBoard, ChessEmbed, get_pgn, get_move
from typing import List, Tuple, Union, TYPE_CHECKING
from aiohttp import ClientSession
from utils.voteutils import random_vote
if TYPE_CHECKING:
    from main import PandasBot

OUTCOMES = {1: "Checkmate", 2: "Stalemate", 3: "Insufficent Material", 4: "75 Moves",
            5: "Fivefold Repetition", 6: "50 Move Rule", 7: "Threefold Repetition"}

TIMECONTROLS = {"25 + 0": [25, False], "10 + 0": [10, False], "5 + 0": [5, False], "3 + 0": [
    3, False], "1 + 0": [1, False], "10 seconds per move": [10, True], "30 seconds per move": [30, True]}


class Chess(commands.Cog, name="Chess", description="The classic battle of the inner brains is on Discord! Test your Chess skills by challenging other members, and play against engines to sharpen these skills. Made so playing on Discord is very easy and enjoyable, play while talking with your friends!"):

    def __init__(self, bot):
        self.bot: PandasBot = bot

    async def check_db(self, ctx: commands.Context, opponent: discord.Member):
        if await self.bot.db.fetchval("SELECT member1 FROM chessgame WHERE ((member1 = $1 OR member1 = $2) OR (member2 = $1 OR member2 = $2)) AND channel = $3", ctx.author.id, opponent.id, ctx.channel.id):
            await ctx.send("You're already in a game in this channel!")
            return False
        return True

    async def chess_check(self, ctx: commands.Context, opponent: discord.Member):
        if ctx.author.bot or opponent.bot or ctx.author == opponent:
            await ctx.send("You can't play chess with bots or yourself!")
            return False
        dbcheck = await self.check_db(ctx, opponent)
        return dbcheck is not False

    @commands.command(name="playchess", aliases=["chess"], help="Challenge another member to play Chess with you. You can make moves using algebreic notation or an easier starting square-ending square notation. Play with a built in timer, resignation, and draw requests all controlled by buttons.", brief="Play chess with another member!")
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.guild)
    async def playchess(self, ctx: commands.Context, opponent: discord.Member = None):
        if opponent is None:
            await ctx.send("Provide someone to play chess with")
            return
        chesscheck = await self.chess_check(ctx, opponent)
        if chesscheck is False:
            return
        tcselect = await list_select(ctx, {"25 + 0": [25, False], "10 + 0": [10, False], "5 + 0": [5, False], "3 + 0": [3, False], "1 + 0": [1, False], "10 seconds per move": [10, True], "30 seconds per move": [30, True]}, "Select your time control", ctx.author, prompt="Select time control.", cancel=True)
        if tcselect is None or tcselect is False:
            return
        permove = TIMECONTROLS[tcselect][1]
        timecontrolname = tcselect
        timecontrol = TIMECONTROLS[tcselect][0] * \
            60 if permove is False else TIMECONTROLS[tcselect][0]
        gamerequest = await request_game(ctx, f"{ctx.author} is challenging you to a chess match with a time control of __{timecontrolname}__. You have 2 minutes to respond or the match will be automatically declined.", opponent)
        if gamerequest is False:
            return
        await self.bot.db.execute("INSERT INTO chessgame VALUES ($1, $2, $3);", ctx.author.id, opponent.id, ctx.channel.id)
        players = random.sample([ctx.author, opponent], 2)
        chessgame = ChessGame(timecontrol, timecontrolname,
                              players, ctx, permove, self.bot.session)
        await chessgame.initial_send()
        await chessgame.game_loop()
        await self.bot.db.execute("DELETE FROM chessgame WHERE member1 = $1 AND member2 = $2 AND channel = $3;", ctx.author.id, opponent.id, ctx.channel.id)


class ChessGame:
    def __init__(self, timecontrol: int, timecontrolname: str, players: List[discord.Member], ctx: commands.Context, permove: bool, session: ClientSession):
        self.board = ChessBoard()
        self.timecontrol = timecontrol
        self.players = players
        self.ctx = ctx
        self.timecontrolname = timecontrolname
        self.sides = [ChessPlayer(players[0], chess.WHITE, timecontrol), ChessPlayer(
            players[1], chess.BLACK, timecontrol)]
        self.chessembed = ChessEmbed(self.sides, self.timecontrolname)
        self.embed = None
        self.gamemsg: Union[None, discord.Message] = None
        self.view: Union[None, ChessMenu] = None
        self.curplayer: ChessPlayer = None
        self.move: Union[chess.Move, None] = None
        self.permove = permove
        self.session = session

    async def initial_send(self):
        self.embed = await self.chessembed.chess_get(self.board, await self.board.boardla_fen(), None)
        self.gamemsg = await self.ctx.send(embed=self.embed)

    async def run_move(self, timeoutnum: int) -> Tuple[bool, Union[chess.Move, Resignation, Draw]]:
        await self.view.wait()

        if (self.view.move is None) and (self.view.result is None):
            if timeoutnum == 300:
                print('ccccc')
                self.curplayer.timecontrol = self.curplayer.timecontrol - \
                    timeoutnum if self.curplayer.timecontrol >= timeoutnum+1 else 0
                if self.view.is_finished is False:
                    self.view.stop()
                return False, TimeResign(self.curplayer, get_other_player(self.curplayer, self.sides), True).create_saying()
            else:
                print('ddddd')
                self.curplayer.timecontrol = 0
                return False, TimeResign(self.curplayer, get_other_player(self.curplayer, self.sides)).create_saying()
        if self.view.result is not None:
            print('eeeee')
            return True, self.view.result
        movelist = await get_move(self.board, self.view.move)
        move: chess.Move = movelist[0]
        if move.promotion is not None and movelist[1] is False:
            print('gaaaaa')
            move.promotion = await self.promotion_view()
        print('ffff')
        return None, move

    def update_time(self, permove: bool, start: int):
        if permove:
            self.curplayer.timecontrol = self.timecontrol
            print('gaaaa')
        else:
            self.curplayer.timecontrol = self.curplayer.timecontrol - \
                (round(time.time()-start))

    async def promotion_view(self):
        promotion = await list_buttons(self.ctx, {"Queen": discord.ButtonStyle.gray, "Rook": discord.ButtonStyle.gray, "Bishop": discord.ButtonStyle.gray, "Knight": discord.ButtonStyle.gray}, self.curplayer.member, prompt="Promote pawn to?", timeout=15, timeouttalk=False)
        print('yaaaaaaa')
        if promotion is None:
            await self.ctx.send("No promotion chosen, automatically promoted to Queen")
            return chess.Piece(chess.QUEEN, self.curplayer.side).piece_type
        pieceshort = promotion[0] if promotion != "Knight" else "N"
        # capital letters = white, lowercase = black
        return chess.Piece.from_symbol(pieceshort if self.curplayer.side == chess.WHITE else pieceshort.lower()).piece_type

    async def get_analysis(self, session: ClientSession, draw=None, outcome: Resignation = None):
        if len(self.board.move_stack) < 10:
            return "Match is too short for analysis board"
        if draw is True:
            saying = "1/2-1/2"
        elif outcome:
            saying = outcome.resignwin.resignoutcome
        else:
            saying = self.board.result(claim_draw=True)
        link = await get_pgn(session, self.board, self.players[0], self.players[1], saying)
        return f"[Analysis Board]({link})" if link else "Analysis board currently unavaliable"

    async def checkmate_draw(self):
        outcome = await self.board.board_outcome(True)
        if outcome.winner is None:
            return f"Draw - {OUTCOMES[outcome.termination.value]} \n {self.sides[0].member.mention} drawed {self.sides[1].member.mention} on {OUTCOMES[outcome.termination.value]}"
        for player in self.sides:
            if player.side == outcome.winner:
                winner = player
            else:
                loser = player
        return f"Checkmate - {winner.sidename} is victorious \n *{outcome.result()}* - {winner.member.mention} defeated {loser.member.mention} on checkmate"

    async def winning_embed(self, saying: str, move: chess.Move, analysis: str):
        white, black = self.sides[0], self.sides[1]
        if self.timecontrolname is None:
            timecontrol = ""
        else:
            timecontrol = f"__Time Control - {self.timecontrolname}__ \n **:clock1: {white.member}:** {datetime.timedelta(seconds=white.timecontrol)} \n **:clock1: {black.member}:** {datetime.timedelta(seconds=black.timecontrol)}"
        embed1 = discord.Embed(
            title=f"Chess Match Complete - {white.member} vs. {black.member}",
            description=f'{saying} \n {timecontrol} \n {analysis}',
            timestamp=discord.utils.utcnow(),
            color=discord.Color.dark_gold(),
        )

        movestring = f"-{move.uci()}" if move != None else ""
        url = f"https://chessboardimage.com/{await self.board.boardla_fen()}{movestring}.png"
        url = url.replace(" ", "%20")
        embed1.set_image(url=url)
        return embed1

    async def finish_game(self, saying: str, analysis: str):
        await self.gamemsg.delete()
        embed = await self.winning_embed(saying, self.move, analysis)
        await self.ctx.send(embed=embed)
        rv = random_vote()
        if rv:
            await ctx.send("P.S... register to vote today.", embed=rv[0], view=rv[1])


    async def player_move(self):
        side = self.curplayer
        timeoutnum = 300 if side.timecontrol > 300 else side.timecontrol+0.1
        print(timeoutnum)
        start = time.time()
        self.view = ChessMenu(
            self.embed, self.sides, side, timeoutnum, start, self.gamemsg, self.board)
        movemsg: discord.Message = await self.ctx.send(f"{side.member.mention} Your move! Proper formats: chess algebreic notation, square from-square to. Examples: exd5, e4-d5", view=self.view)
        waitresult, result = await self.run_move(timeoutnum)
        if self.view.message is not None and self.gamemsg != self.view.message:
            self.gamemsg = self.view.message
        await movemsg.delete()
        sanmove, finished, analysis, saying = None, False, None, None
        if waitresult is False:
            finished = True
            analysis = await self.get_analysis(self.session, outcome=result)
            saying = result
        elif waitresult is True:
            self.update_time(self.permove, start)
            analysis = await self.get_analysis(self.session, draw=True if self.view.drawresult else None, outcome=result)
            saying = self.view.result.create_saying()
            finished = True
        else:
            self.move = result
            self.update_time(self.permove, start)
            sanmove = await self.board.board_move_to_san(self.move)
        return sanmove, analysis, saying, finished

    async def game_loop(self):
        x = True
        while x:
            for side in self.sides:
                self.curplayer = side
                sanmove, analysis, saying, finished = await self.player_move()
                if finished:
                    x = False
                    break
                await self.board.board_push(self.move)
                if await self.board.board_gameover(True) is True:
                    analysis = await self.get_analysis(self.session)
                    saying = await self.checkmate_draw()
                    x = False
                    break
                self.embed = await self.chessembed.chess_get(sanmove, await self.board.boardla_fen(), f"-{self.move.uci()}")
                await self.gamemsg.edit(embed=self.embed)

            if not x:
                await self.finish_game(saying, analysis)
                return


async def setup(bot: PandasBot):
    await bot.add_cog(Chess(bot))
