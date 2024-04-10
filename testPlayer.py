from catanatron import Player
from catanatron import RandomPlayer
from catanatron_experimental.cli.cli_players import register_player
from catanatron_experimental.machine_learning.players.minimax import SameTurnAlphaBetaPlayer
from catanatron_experimental.machine_learning.players.tree_search_utils import (expand_spectrum, list_prunned_actions)
from catanatron.models.player import Color
from catanatron.state_functions import (
    get_player_buildings,
    get_player_freqdeck,
    player_can_afford_dev_card,
    player_can_play_dev,
    player_has_rolled,
    player_key,
    player_num_resource_cards,
    player_resource_freqdeck_contains,
)
from catanatron.models.enums import (
    RESOURCES,
    Action,
    ActionPrompt,
    ActionType,
    BRICK,
    ORE,
    FastResource,
    SETTLEMENT,
    SHEEP,
    WHEAT,
    WOOD,
)
import random
import copy

# HELPER FUNCTIONS

def addTradeAction(self, game, playable_actions):
    """
    Adds a trade action to a list of playable actions. The check to ensure that the action
    would be valid should be done before this called.
    """
    hand_freqdeck = [
        player_num_resource_cards(game.state, self.color, resource) for resource in RESOURCES
    ]

    trade_action = createMostForLeastTrade(self, hand_freqdeck)

    if trade_action != None:
        playable_actions.append(trade_action)

    return playable_actions
    
def createMostForLeastTrade(self, hand_freqdeck):
    """
    Creates a trade action the will trade the resource the player has the most of for the 
    resource the player has the least of.
    """

    # Trackers for least and most resource indices and amounts
    least_index = -1
    least_amount = 100
    most_index = -1
    most_amount = 0

    # Find least resource
    for index, resource in enumerate(RESOURCES):
        amount = hand_freqdeck[index]

        if amount < least_amount:
            least_index = index
            least_amount = amount

    # Find most resource, need to be done separately for least to ensure that most and least are not the same index
    for index, resource in enumerate(RESOURCES):
        amount = hand_freqdeck[index]

        if amount > most_amount and index != least_index:
            most_index = index
            most_amount = amount

    # Create empty trade list
    trade_list = [0] * 10

    # Check if the player has at least one card
    if most_index != -1:
        # Set indices in trade list to determine resources traded
        trade_list[most_index] = 1
        trade_list[least_index + 5] = 1

        # Convert list to tuple and create action
        trade_value = tuple(trade_list)
        trade_action = Action(self.color, ActionType.OFFER_TRADE, trade_value)
    else: 
        trade_action = None

    return trade_action


# AlphaBeta Player DOES NOT WORK
# ALPHABETA DOES NOT HAVE FUNCTIONALITY TO PROCESS TRADE UTILITY (expand_spectrum)
@register_player("FOO")
class FooPlayer(SameTurnAlphaBetaPlayer):

    def get_actions(self, game):
    # Values for all three is a 10-resource tuple, first 5 is offered freqdeck, last 5 is receiving freqdeck.
    # Offered (0 - 4): [WOOD, BRICK, SHEEP, WHEAT, ORE]
    # Offered (5 - 9): [WOOD, BRICK, SHEEP, WHEAT, ORE]

        # insert trade utility function here

        temp = game.state.playable_actions

        if self.prunning:

          #return list_prunned_actions(game)
          temp = list_prunned_actions(game)
          temp = self.trade_temp(game)
          return temp

        #return game.state.playable_actions
        temp = self.trade_temp(game)
        return temp

    def trade_temp(self, game):
        color = game.state.current_color()
        key = player_key(game.state, color)

        temp = game.state.playable_actions

        if game.state.player_state[f"{key}_WOOD_IN_HAND"] > 0:

            tempAction = Action(color, ActionType.OFFER_TRADE, (1, 0, 0, 0, 0, 0, 0, 0, 0, 1))

            if temp is None:
                temp = [tempAction]

            else:
                temp.append(tempAction)

            return temp

        return temp


# Based on RandomPlayer
@register_player("FOO2")
class FooPlayer(RandomPlayer):

    def __init__(self, color):
        super().__init__(color)
        self.traded = False

    def decide(self, game, playable_actions):
        print("Start of decide function")
        # Values for all three is a 10-resource tuple, first 5 is offered freqdeck, last 5 is receiving freqdeck.
        # Offered (0 - 4): [WOOD, BRICK, SHEEP, WHEAT, ORE]
        # Offered (5 - 9): [WOOD, BRICK, SHEEP, WHEAT, ORE]

        temp = self.trade_temp(game)
        c = random.choice(temp)

        if c.action_type == ActionType.END_TURN:
            self.traded = False

        return random.choice(temp)

    def trade_temp(self, game):
        state = game.state
        color = state.current_color()
        key = player_key(game.state, color)

        temp = game.state.playable_actions

        if state.player_state[f"{key}_WOOD_IN_HAND"] > 0 and player_has_rolled(state, color) and state.current_prompt == ActionPrompt.PLAY_TURN and self.traded is False:
            #raise ValueError("fuck")
            tempAction = Action(color, ActionType.OFFER_TRADE, (1, 0, 0, 0, 0, 0, 0, 0, 0, 1))
            self.traded = True

            if temp is None:
                temp = [tempAction]

            else:
                temp.append(tempAction)

            return temp

        return temp
    

# Based on RandomPlayer
@register_player("Trader")
class TraderBotPlayer(Player):
    """Random AI player that selects an action randomly from the list of playable_actions.
        Additionally has the chance to trade resource they have the most of for the resource 
        they have the least of."""

    def __init__(self, color, is_bot=True):
        # The color of the player
        self.color = color
        # Whether or not the player is controlled by a bot
        self.is_bot = is_bot
        # Whether or not the player has traded this turn
        self.tradeAttempted = False

    def decide(self, game, playable_actions):
        # Add possible trade action if the player has rolled
        if player_has_rolled(game.state, self.color) and game.state.current_prompt == ActionPrompt.PLAY_TURN and self.traded == False:
            playable_actions = addTradeAction(self, game, playable_actions)

        # Choose a random action from possible actions
        choice = random.choice(playable_actions)

        # Maintain tracker to know if player has traded this turn
        if choice.action_type == ActionType.ROLL:
            self.traded = False
        if choice.action_type == ActionType.OFFER_TRADE:
            self.traded = True

        return choice
    

WEIGHTS_BY_ACTION_TYPE = {
    ActionType.BUILD_CITY: 10000,
    ActionType.BUILD_SETTLEMENT: 1000,
    ActionType.OFFER_TRADE: 500,
    ActionType.BUY_DEVELOPMENT_CARD: 100,
}

# Based on WeightedRandomPlayer
@register_player("WeightedTrader")
class WeightedTraderRandomPlayer(Player):
    """
    Player that decides at random, but skews distribution
    to actions that are likely better (cities > settlements > dev cards).
    """

    def __init__(self, color, is_bot=True):
        # The color of the player
        self.color = color
        # Whether or not the player is controlled by a bot
        self.is_bot = is_bot
        # Whether or not the player has traded this turn
        self.tradeAttempted = False

    def decide(self, game, playable_actions):
        # Add possible trade action if the player has rolled
        if player_has_rolled(game.state, self.color) and game.state.current_prompt == ActionPrompt.PLAY_TURN and self.traded == False:
            playable_actions = addTradeAction(self, game, playable_actions)

        # Add weights to choices 
        bloated_actions = []
        for action in playable_actions:
            weight = WEIGHTS_BY_ACTION_TYPE.get(action.action_type, 1)
            bloated_actions.extend([action] * weight)

        # Choose a random action from possible weighted actions
        choice = random.choice(bloated_actions)

        # Maintain tracker to know if player has traded this turn
        if choice.action_type == ActionType.ROLL:
            self.traded = False
        if choice.action_type == ActionType.OFFER_TRADE:
            self.traded = True
        
        return choice
