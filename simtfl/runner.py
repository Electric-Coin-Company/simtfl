import simpy

def clock(env, name, tick):
    while True:
        print(name, env.now)
        yield env.timeout(tick)

def run():
    print("This is just the minimal example for simpy.")
    env = simpy.Environment()
    env.process(clock(env, 'fast', 0.5))
    env.process(clock(env, 'slow', 1))
    env.run(until=2)
