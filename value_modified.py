from enum import Enum
import random
import numpy as np

from catanatron.models.player import Player
from catanatron.models.enums import RESOURCES
from catanatron_experimental.cli.cli_players import register_player
from catanatron_experimental.machine_learning.players.value import get_value_fn

from catanatron.state_functions import (
    get_enemy_colors,
    player_has_rolled,
    player_freqdeck_add,
    player_freqdeck_subtract,
    player_num_resource_cards,
    player_resource_freqdeck_contains,
)

from catanatron.models.enums import (
    RESOURCES,
    Action,
    ActionPrompt,
    ActionType,
)

######################################################################
# HELPER VARIABLES AND ENUMS
######################################################################

WEIGHTS_BY_ACTION_TYPE = {
    ActionType.BUILD_CITY: 10000,
    ActionType.BUILD_SETTLEMENT: 1000,
    ActionType.OFFER_TRADE: 500,
    ActionType.BUY_DEVELOPMENT_CARD: 100,
}

class TradeType(Enum):
    MostForLeast       = 1
    PortResource       = 2
    RoadPriority       = 3
    SettlementPriority = 4
    CityPriority       = 5

######################################################################
# TRADE UTILITY FUNCTIONS
######################################################################

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
        if flag == TradeType.MostForLeast:
            trade_actions = createMostForLeastTrade(self, hand_freqdeck)
        elif flag == TradeType.PortResource:
            trade_actions = createPortResourceTrade(self, game, hand_freqdeck)
        elif flag == TradeType.RoadPriority:
            trade_actions = createRoadPriorityTrade(self, game, hand_freqdeck)
        elif flag == TradeType.SettlementPriority:
            trade_actions = createSettlementPriorityTrade(self, game, hand_freqdeck)
        elif flag == TradeType.CityPriority:
            trade_actions = createCityPriorityTrade(self, game, hand_freqdeck)

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

def createRoadPriorityTrade(self, game, hand_freqdeck):
    """
    Creates a trade action that will trade for resources need to build a road
    Function Flag to Include in Players: RoadPriority
    """
    # List of possible trade actions
    trade_actions = []

    # generate actions for trading for wood
    if hand_freqdeck[0] < 1:
        for i in range(len(hand_freqdeck)):
            trade_value = [0, 0, 0, 0, 0, 1, 0, 0, 0, 0]

            # makes sure the trade isn't wood for wood
            if i != 0:
                # if trading brick, make sure the trade doesn't leave agent with no brick
                if i == 1 and hand_freqdeck[1] > 1:
                    trade_value[i] = 1
                    trade_actions.append(Action(self.color, ActionType.OFFER_TRADE, trade_value))

                elif hand_freqdeck[i] > 0:
                    trade_value[i] = 1
                    trade_actions.append(Action(self.color, ActionType.OFFER_TRADE, trade_value))

    # generate actions for trading for wood
    if hand_freqdeck[1] < 1:
        for i in range(len(hand_freqdeck)):
            trade_value = [0, 0, 0, 0, 0, 0, 1, 0, 0, 0]

            # makes sure the trade isn't brick for brick
            if i != 1:
                # if trading brick, make sure the trade doesn't leave agent with no wood
                if i == 0 and hand_freqdeck[0] > 1:
                    trade_value[i] = 1
                    trade_actions.append(Action(self.color, ActionType.OFFER_TRADE, trade_value))

                elif hand_freqdeck[i] > 0:
                    trade_value[i] = 1
                    trade_actions.append(Action(self.color, ActionType.OFFER_TRADE, trade_value))

    return trade_actions

def createSettlementPriorityTrade(self, game, hand_freqdeck):
    """
    Creates a trade action that will trade for resources need to build a settlement
    resource the player has the least of.
    Function Flag to Include in Players: SettlementPriority
    """
    # List of possible trade actions
    trade_actions = []

    # generate actions for trading for wood

    # resource to gain from trade
    for gain in range(len(hand_freqdeck)):
        trade_value = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        # checks to see if resource isn't ore and none of the resource is owned
        if gain != 4 and hand_freqdeck[gain] < 1:
            trade_value[4 + gain] = 1

            # resource to trade away
            for offer in range(len(hand_freqdeck)):

                # checks if resource isn't ore and that at least two are owned
                if offer != 4 and gain != offer and hand_freqdeck[offer] > 1:
                    trade_value[offer] = 1
                    trade_actions.append(Action(self.color, ActionType.OFFER_TRADE, trade_value))

                # checks if resource is ore and at least one is owned
                elif offer == 4 and hand_freqdeck[offer] > 0:
                    trade_value[offer] = 1
                    trade_actions.append(Action(self.color, ActionType.OFFER_TRADE, trade_value))

    return trade_actions

def createCityPriorityTrade(self, game, hand_freqdeck):
    """
    Creates a trade action that will trade for resources need to build a city
    resource the player has the least of.
    Function Flag to Include in Players: CityPriority
    """
    # List of possible trade actions
    trade_actions = []

    # generate actions for trading for wood

    # resource to gain from trade
    for gain in range(len(hand_freqdeck)):
        trade_value = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        # checks to see if resource is wheat and less than 2 are owned or ore and less than 3 are owned
        if (gain == 3 and hand_freqdeck[gain] < 2) or (gain == 4 and hand_freqdeck[gain] < 3):
            trade_value[4 + gain] = 1

            # resource to trade away
            for offer in range(len(hand_freqdeck)):

                # checks if resource isn't ore and that at least one are owned
                if offer != 3 or offer != 4 and gain != offer and hand_freqdeck[offer] > 0:
                    trade_value[offer] = 1
                    trade_actions.append(Action(self.color, ActionType.OFFER_TRADE, trade_value))

                # checks if resource is wheat and that at least two are owned
                elif offer == 3 and hand_freqdeck[offer] > 2:
                    trade_value[offer] = 1
                    trade_actions.append(Action(self.color, ActionType.OFFER_TRADE, trade_value))

                # checks if resource is ore and that at least three are owned
                elif offer == 4 and hand_freqdeck[offer] > 3:
                    trade_value[offer] = 1
                    trade_actions.append(Action(self.color, ActionType.OFFER_TRADE, trade_value))

    return trade_actions


######################################################################
# CUSTOM PLAYERS
######################################################################

# Modified ValueFunctionPlayer, it can offer trades

@register_player("ValuePlayerModified") # COMMENT THIS OUT WHEN TESTING WITH DEBUGGER, WHEN USING CLI UNCOMMENT THIS
class ValueFunctionPlayerModified(Player): 
    """
    Player that selects the move that maximizes a heuristic value function.

    For now, the base value function only considers 1 enemy player.
    """

    def __init__(
        self, color, value_fn_builder_name=None, params=None, is_bot=True, epsilon=None
    ):
        super().__init__(color, is_bot)
        self.value_fn_builder_name = (
            "contender_fn" if value_fn_builder_name == "C" else "base_fn"
        )
        self.params = params
        self.epsilon = epsilon
        self.traded = False
        self.tradeAttempted = False
        
        # Utility Functions to include for trading
        self.function_flags = [
            TradeType.MostForLeast,
            TradeType.PortResource,
            TradeType.RoadPriority,
            # TradeType.SettlementPriority,
            TradeType.CityPriority
        ]

    def execute_trade(self, game, enemy_color, offered, recieved):
        # Modify players resources, minus the offered, add the received
        player_freqdeck_add(game.state, self.color, recieved)
        player_freqdeck_subtract(game.state, self.color, offered)

        # Modify enemy resources, add the offered, minus the received
        player_freqdeck_subtract(game.state, enemy_color, recieved)
        player_freqdeck_add(game.state, enemy_color, offered)

    def decide(self, game, playable_actions):
        if len(playable_actions) == 1:
            return playable_actions[0]
        
        # Add trades to list of playable actions
        if player_has_rolled(game.state, self.color) and game.state.current_prompt == ActionPrompt.PLAY_TURN and self.traded == False:
            playable_actions = addTradeAction(self, game, playable_actions)

        # Random probability of choosing a random action, if enabled.
        if self.epsilon is not None and random.random() < self.epsilon:
            return random.choice(playable_actions)


        action_values = np.zeros(len(playable_actions))
        for i, action in enumerate(playable_actions): # + tradeable_actions:
            if action.action_type == ActionType.OFFER_TRADE:

                # Check which player can make the trade
                enemy_colors = get_enemy_colors(game.state.colors, self.color)
                for enemy_color in enemy_colors:
                    
                    # Offered (0 - 4): [WOOD, BRICK, SHEEP, WHEAT, ORE]
                    # Offered (5 - 9): [WOOD, BRICK, SHEEP, WHEAT, ORE]
                    # Check if they can make the trade
                    offered_resources   = action.value[:5]
                    received_resources  = action.value[5:]                   
                    can_trade = player_resource_freqdeck_contains(game.state, enemy_color, received_resources)
                    if not can_trade:
                        action_values[i] = float('-inf')
                        continue

                    
                    game_copy = game.copy()
                    self.execute_trade(game_copy, enemy_color, offered_resources, received_resources)

                    value_fn = get_value_fn(self.value_fn_builder_name, self.params)
                    value = value_fn(game_copy, self.color)
                    action_values[i] = value
                

            else:
                game_copy = game.copy()
                game_copy.execute(action)

                value_fn = get_value_fn(self.value_fn_builder_name, self.params)
                value = value_fn(game_copy, self.color)
                action_values[i] = value
        
        best_idx = np.argmax(action_values)
        best_action = playable_actions[best_idx]

        # Keep track of whether or not the bot has offer a trade
        if best_action.action_type == ActionType.ROLL:
            self.traded = False
        if best_action.action_type == ActionType.OFFER_TRADE:
            print('Best action is trade')
            self.traded = True

        return best_action

    def __str__(self):
        return super().__str__() + f"(value_fn={self.value_fn_builder_name})"
    
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
