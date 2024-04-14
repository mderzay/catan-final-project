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
    # Get player hand
    hand_freqdeck = [
        player_num_resource_cards(game.state, self.color, resource) for resource in RESOURCES
    ]

    for flag in self.function_flags:
        # Create list of possible trade actions
        trade_actions = []

        # Add possible trade actions per utility function
        if flag == "MostForLeast":
            trade_actions = createMostForLeastTrade(self, hand_freqdeck)
        elif flag == "PortResource":
            trade_actions = createPortResourceTrade(self, game, hand_freqdeck)

        # If the list is not empty, add trade actions to playable actions 
        if trade_actions:
            playable_actions.extend(trade_actions)

    return playable_actions
    

def createMostForLeastTrade(self, hand_freqdeck):
    """
    Creates a trade action the will trade the resource the player has the most of for the 
    resource the player has the least of.
    Function Flag to Include in Players: MostforLeast
    """
    # List of possible trade actions
    trade_actions = []

    # Trackers for least and most resource indices and amounts
    least_indices = []
    least_amount = 100
    most_indices = []
    most_amount = -1

    # Find least and most resource
    for index, resource in enumerate(RESOURCES):
        amount = hand_freqdeck[index]

        # Check for least resource
        if amount < least_amount:
            least_indices = [index]
            least_amount = amount
        elif amount == least_amount:
            least_indices.append(index)

        # Check for most resouce
        if amount > most_amount:
            most_indices = [index]
            most_amount = amount
        elif amount == most_amount:
            most_indices.append(index)

    # Check that the player has at least one card and not all resource have the same count
    if most_amount == 0 or most_amount == least_amount:
        most_indices = []

    # Check for valid amounts
    if most_indices:
        # For each combination of most index and least index
        for most_index in most_indices:
            for least_index in least_indices:

                # Add a trade action for each value that could be traded for the most resource
                for amount in range(1, most_amount + 1):
                    # Create empty trade list
                    trade_list = [0] * 10

                    # Set indices in trade list to determine resources traded
                    trade_list[most_index] = amount
                    trade_list[least_index + 5] = amount

                    # Convert list to tuple and create action
                    trade_value = tuple(trade_list)
                    trade_actions.append(Action(self.color, ActionType.OFFER_TRADE, trade_value))

    return trade_actions


def createPortResourceTrade(self, game, hand_freqdeck):
    """
    Creates a trade action the will trade for the resource that the player owns a
    port of.
    Function Flag to Include in Players: PortResource
    """
    # List of possible trade actions
    trade_actions = []

    # Trackers for resources of owned and nonowned ports
    owned_indices = []
    non_owned_indices = []

    # Determine ports player has
    port_resources = game.state.board.get_player_port_resources(self.color)

    # Check for return value
    if port_resources:
        # Add indices per resource to owned ports
        for resource in port_resources:
            if resource == "WOOD":
                owned_indices.append(0)
            elif resource == "BRICK":
                owned_indices.append(1)
            elif resource == "SHEEP":
                owned_indices.append(2)
            elif resource == "WHEAT":
                owned_indices.append(3)
            elif resource == "ORE":
                owned_indices.append(4)

        # Check that at least one port is owned
        if owned_indices:
            # Put the remaining indices in the non owned list
            for index in range(5):
                if index not in owned_indices:
                    non_owned_indices.append(index)
                
            # For each combination of most index and least index
            for owned_index in owned_indices:
                for non_owned_index in non_owned_indices:
                    
                    # Check the amount that can be traded
                    amount = hand_freqdeck[non_owned_index]
                    if amount > 0:
                        # Add a trade action for each value that could be traded for the most resource
                        for amount in range(1, amount + 1):
                            # Create empty trade list
                            trade_list = [0] * 10

                            # Set indices in trade list to determine resources traded
                            trade_list[non_owned_index] = amount
                            trade_list[owned_index + 5] = amount

                            # Convert list to tuple and create action
                            trade_value = tuple(trade_list)
                            trade_actions.append(Action(self.color, ActionType.OFFER_TRADE, trade_value))

    return trade_actions


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
        self.trade_attempted = False
        # Utility Functions to include for trading
        self.function_flags = [
            "MostForLeast",
            "PortResource",
        ]

    def decide(self, game, playable_actions):
        # Add possible trade action if the player has rolled
        if player_has_rolled(game.state, self.color) and game.state.current_prompt == ActionPrompt.PLAY_TURN and self.trade_attempted == False:
            playable_actions = addTradeAction(self, game, playable_actions)

        # Choose a random action from possible actions
        choice = random.choice(playable_actions)

        # Maintain tracker to know if player has traded this turn
        if choice.action_type == ActionType.ROLL:
            self.trade_attempted = False
        if choice.action_type == ActionType.OFFER_TRADE:
            self.trade_attempted = True

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
        self.trade_attempted = False
        # Utility Functions to include for trading
        self.function_flags = [
            "MostForLeast",
            "PortResource",
        ]

    def decide(self, game, playable_actions):
        # Add possible trade action if the player has rolled
        if player_has_rolled(game.state, self.color) and game.state.current_prompt == ActionPrompt.PLAY_TURN and self.trade_attempted == False:
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
            self.trade_attempted = False
        if choice.action_type == ActionType.OFFER_TRADE:
            self.trade_attempted = True
        
        return choice
