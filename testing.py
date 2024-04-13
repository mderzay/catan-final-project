from value_modified import ValueFunctionPlayerModified 
from catanatron import Game, RandomPlayer, Color

players = [
    ValueFunctionPlayerModified(Color.BLUE),
    RandomPlayer(Color.RED)
]

game = Game(players)
print(game.play())