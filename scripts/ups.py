"""
Custom ups script(?)
Yes its pretty trick stuff, please dont touch and dont insult me
im lazy as fuck to think in a better method, so haha cheers ;)

by sByte
"""

import asyncio
from pyspades.contained import WorldUpdate
from pyspades.protocol import BaseProtocol
import traceback
import time
from twisted.logger import Logger
from piqueserver.commands import command

log = Logger()

MAX_UPS = 60
UPDATE_FREQUENCY = 1/(MAX_UPS+70)

@command("ups")
def ups(p, ups=MAX_UPS):
	try:
		ups = int(ups)
	except:
		return "You can only use ints as parameter."

	p.send_chat("You changed your UPS from %i to %i."%(p.ups, ups))
	p.ups = ups


def apply_script(protocol, connection, config):
	class upsProtocol(protocol):
		trick_ups = 0
		async def update(self):
			while True:
				start_time = time.monotonic()
				# Notify if update starts more than 4ms later than requested
				lag = start_time - self.world_time - UPDATE_FREQUENCY

				if lag > 0.004:
					log.debug("LAG before world update: {lag:.0f} ms", lag=lag * 1000)

				BaseProtocol.update(self)
				# Map transfer
				for player in self.connections.values():
					if (player.map_data is not None and
							not player.peer.reliableDataInTransit):
						player.continue_map_transfer()
				# Update world
				while (time.monotonic() - self.world_time) > UPDATE_FREQUENCY:
					self.loop_count += 1
					self.world.update(UPDATE_FREQUENCY)
					try:
						self.on_world_update()
					except Exception:
						traceback.print_exc()
					self.world_time += UPDATE_FREQUENCY
				# Update network
				if time.monotonic() - self.last_network_update >= 1 / MAX_UPS:
					self.trick_ups+=1
					self.update_network()

					if self.trick_ups >= MAX_UPS:
						self.trick_ups = 0
					self.last_network_update = self.world_time

				# Notify if update uses more than 70% of time budget
				lag = time.monotonic() - start_time
				if lag > (UPDATE_FREQUENCY * 0.7):
					log.debug("world update LAG: {lag:.0f} ms", lag=lag * 1000)

				delay = self.world_time + UPDATE_FREQUENCY - time.monotonic()
				await asyncio.sleep(delay)

		def update_network(self):
			if not len(self.players):
				return
			items = []
			highest_player_id = max(self.players)
			for i in range(highest_player_id + 1):
				position = orientation = None
				try:
					player = self.players[i]
					if (not player.filter_visibility_data and
							not player.team.spectator):
						world_object = player.world_object
						position = world_object.position.get()
						orientation = world_object.orientation.get()
				except (KeyError, TypeError, AttributeError):
					pass
				if position is None:
					position = (0.0, 0.0, 0.0)
					orientation = (0.0, 0.0, 0.0)
				items.append((position, orientation))
			world_update = WorldUpdate()
			# we only want to send as many items of the player list as needed, so
			# we slice it off at the highest player id
			world_update.items = items[:highest_player_id+1]

			for player in self.connections.values():
				if not player or player.player_id is None:
					continue

				if self.trick_ups <= player.ups:
					player.send_contained(world_update, True)

	class upsConnec(connection):
		ups = 10

		def on_team_join(self, team):
			self.ups = MAX_UPS
			return connection.on_team_join(self, team)

	return upsProtocol, upsConnec
