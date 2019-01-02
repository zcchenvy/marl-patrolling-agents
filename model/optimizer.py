from utils import sample_batch_history
import torch
import torch.nn.functional as F




# if gpu is to be used
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def optimize_model(env, batch_size, episode):
    for agent in env.agents:
        if agent.can_learn:
            batch = sample_batch_history(agent, batch_size)
            non_final_mask = torch.tensor(tuple(map(lambda s: s is not None,
                                                    batch["next_states"])), device=device, dtype=torch.uint8)



            h = len(batch["next_states"][0])

            non_final_next_states = torch.FloatTensor(batch["next_states"], device=device).reshape(batch_size, h * h)


            state_batch = torch.FloatTensor(batch["states"], device=device)
            action_batch = torch.FloatTensor(batch["actions"], device=device)
            reward_batch = torch.FloatTensor(batch["rewards"], device=device)



            # Compute Q(s_t, a) - the model computes Q(s_t), then we select the
            # columns of actions taken. These are the actions which would've been taken
            # for each batch state according to policy_net

            state_batch = state_batch.reshape(batch_size, h * h)
            state_action_values = agent.policy_net(state_batch.cuda()).gather(1, action_batch.long().cuda())
            # Compute V(s_{t+1}) for all next states.
            # Expected values of actions for non_final_next_states are computed based
            # on the "older" target_net; selecting their best reward with max(1)[0].
            # This is merged based on the mask, such that we'll have either the expected
            # state value or 0 in case the state was final.
            next_state_values = torch.zeros(batch_size, device=device)



            next_state_values[non_final_mask] = agent.target_net(non_final_next_states.cuda()).max(1)[0].detach()
            # Compute the expected Q values



            expected_state_action_values = (next_state_values * agent.gamma) + reward_batch.cuda() + 0.5

            final = torch.zeros(batch_size, 9).cuda().scatter_(1, expected_state_action_values.reshape(batch_size,1).long(), 1)
            # Compute Huber loss
            loss = F.smooth_l1_loss(state_action_values, final)
            agent.loss_values.append(loss.item())
            agent.reward_values.append(reward_batch.mean())

            # Optimize the model
            agent.optimizer.zero_grad()
            loss.backward()
            for param in agent.policy_net.parameters():
                param.grad.data.clamp_(-1, 1)
            agent.optimizer.step()

            if episode % 100 == 0:
                agent.target_net.load_state_dict(agent.policy_net.state_dict())