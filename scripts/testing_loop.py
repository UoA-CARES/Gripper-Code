
"""
This is an example script that shows how one uses the cares reinforcement learning package.
To run this specific example, move the file so that it is at the same level as the package root
directory
    -- script.py
    -- summer_reinforcement_learning/
"""

#network
#memory replays 

#TODO: training loop, selecting an action, exploration phase, create environment 
#TODO: track the error messages so i know when things are breaking
#TODO: add a plot of episode reward

from cares_reinforcement_learning.networks import TD3
from cares_reinforcement_learning.util import MemoryBuffer
#TODO: figure out why this isnt working
#from cares_reinforcement_learning.examples.Actor import Actor
#from cares_reinforcement_learning.examples.Critic import Critic

#from  Gripper import Gripper
from gripper_environment import Environment
import numpy as np
from argparse import ArgumentParser
import random
import matplotlib.pyplot as plt
#from Servo import Servo
#from Camera import Camera

import torch
import torch.nn as nn
import torch.optim as optim

if torch.cuda.is_available():
    DEVICE = torch.device('cuda')
    print("Working with GPU")
else:
    DEVICE = torch.device('cpu')
    print("Working with CPU")


#BUFFER_CAPACITY = 10

GAMMA = 0.995
TAU = 0.005

ACTOR_LR = 1e-4
CRITIC_LR = 1e-3

#EPISODE_NUM = 10
#BATCH_SIZE = 8  #32 good

MAX_ACTIONS = np.array([1023, 750, 750, 1023, 750, 750, 1023, 750, 750])  #have generalised this to 750 for lower joints for consistency
MIN_ACTIONS = np.array([0, 250, 250, 0, 250, 250, 0, 250, 250]) #have generalised this to 250 for lower joints for consistency

env = Environment()


#need to move these
class Actor(nn.Module):

    def __init__(self, observation_size, num_actions, learning_rate, max_action):
        super(Actor, self).__init__()

        self.max_action = max_action

        self.hidden_size = [128, 64, 32]

        self.h_linear_1 = nn.Linear(in_features=observation_size, out_features=self.hidden_size[0])
        self.h_linear_2 = nn.Linear(in_features=self.hidden_size[0], out_features=self.hidden_size[1])
        self.h_linear_3 = nn.Linear(in_features=self.hidden_size[1], out_features=self.hidden_size[2])
        self.h_linear_4 = nn.Linear(in_features=self.hidden_size[2], out_features=num_actions)

        self.optimiser = optim.Adam(self.parameters(), lr=learning_rate)

    def forward(self, state):
        x = torch.relu(self.h_linear_1(state))
        x = torch.relu(self.h_linear_2(x))
        x = torch.relu(self.h_linear_3(x))
        x = torch.sigmoid(self.h_linear_4(x))
        return x

class Critic(nn.Module):
    def __init__(self, observation_size, num_actions, learning_rate):
        super(Critic, self).__init__()

        self.hidden_size = [128, 64, 32]

        self.Q1 = nn.Sequential(
            nn.Linear(observation_size + num_actions, self.hidden_size[0]),
            nn.ReLU(),
            nn.Linear(self.hidden_size[0], self.hidden_size[1]),
            nn.ReLU(),
            nn.Linear(self.hidden_size[1], self.hidden_size[2]),
            nn.ReLU(),
            nn.Linear(self.hidden_size[2], 1)
        )

        self.optimiser = optim.Adam(self.parameters(), lr=learning_rate)
        self.loss = nn.MSELoss()

    def forward(self, state, action):
        x = torch.cat([state, action], dim=1)
        q1 = self.Q1(x)
        return q1



def main():

    observation_size = 10  

    action_num = 9

    #setup the grippers
    args = parse_args()
    
    # TODO: change this once i change the max min thing in the servo class
    max_actions = MAX_ACTIONS
    min_actions = MIN_ACTIONS

    memory = MemoryBuffer(args.buffer_capacity)

    actor = Actor(observation_size, action_num, ACTOR_LR, max_actions)
    critic_one = Critic(observation_size, action_num, CRITIC_LR)
    critic_two = Critic(observation_size, action_num, CRITIC_LR)

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    random.seed(args.seed)

    td3 = TD3(
        actor_network=actor,
        critic_one=critic_one,
        critic_two=critic_two,
        max_actions=max_actions,
        min_actions=min_actions,
        gamma=GAMMA,
        tau=TAU,
        device=DEVICE
    )

    print(f"Filling Buffer...")

    fill_buffer(memory)

    train(td3, memory)


def train(td3, memory: MemoryBuffer):

    args = parse_args()

    historical_reward = []

    state = env.gripper.home()
    #make this better but i believe its just for this one
    state.append(-1)

    for episode in range(0, args.episode_num):

        #WHERE DOES IT PICK THE ACTION 
        #map state values to 0 - 1 
        for i in range(0, len(state)):
            #print(type(state))
            #print(state)
            state[i] = (state[i])/360
        
            
        episode_reward = 0
        print(f"episode {episode}")
        #print(state) 
        Done = False
        action_taken = 0
        target_angle = np.random.randint(0, 360)

        while action_taken < 15: 

            # Select an Action
            #td3.actor_net.eval() --> dont need bc we are not using batch norm???
            with torch.no_grad():
                
                state_tensor = torch.FloatTensor(state) 
                
                state_tensor = state_tensor.to(DEVICE)
                action = td3.forward(state_tensor) #potientially a naming conflict
                action = action.numpy()

            td3.actor_net.train(True)

            #convert actor output to valid integer steps within the max and min
            for i in range(0, len(action)):
                #map 0 - 1 to min - max
                action[i] = (action[i]) * (MAX_ACTIONS[i] - MIN_ACTIONS[i]) + MIN_ACTIONS[i]
            #print(f"action after being converted from 0-1 {action}")
            action = action.astype(int)
            
            

            next_state, reward, Done = env.step(action, target_angle)
            print(f"next_state {next_state}, reward {reward}, Done {Done}")
            
            memory.add(state, action, reward, next_state, Done)

            experiences = memory.sample(args.batch_size)
            #print(f"experiences {experiences}")
            for _ in range(0, 10): #can be bigger
                #print("learning")
                td3.learn(experiences)

            action_taken += 1
            print(f"actions taken = {action_taken}")

            state = next_state
            episode_reward += reward 

            #this needs to be refactored because it isn't the best code
            

        historical_reward.append(episode_reward)
        plt.plot(historical_reward)
        print(f"Episode #{episode} Reward {episode_reward}")
    plt.show()


def fill_buffer(memory):

    env.gripper.setup()
    state = env.gripper.home()
 
    while len(memory.buffer) < memory.buffer.maxlen:
      
            
        # TODO: refactor the code surely i can make it better than this
        action = np.zeros(9)
    
        for i in range(0, len(MAX_ACTIONS)):
            action[i] = np.random.randint(MIN_ACTIONS[i], MAX_ACTIONS[i])

        action = action.astype(int)
        #pick a random target angle
        target_angle = np.random.randint(0, 360)
        #TODO: would be good to have a thing here to add a thing to the memory if the actions terminated

        next_state, reward, done = env.step(action, target_angle)
        
        #update the policy here?????

        memory.add(state, action, reward, next_state, done)

        #how full is the buffer?
        print(f"Buffer: {len(memory.buffer)} / {memory.buffer.maxlen}", end='\r')
        

        state = next_state

def parse_args():
    parser = ArgumentParser()
    parser.add_argument("--seed", type=int, default=6969)
    parser.add_argument("--batch_size", type=int, default=3)
    parser.add_argument("--buffer_capacity", type=int, default=10)
    parser.add_argument("--episode_num", type=int, default=10)

    args = parser.parse_args()
    return args



if __name__ == '__main__':
    main()