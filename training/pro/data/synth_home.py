"""Synthetic 9 Home-Appliance rows from an independent generator (own homes, rooms, devices, request wordings,
scenario implementations). Only the question framing (question texts, option texts, k_<hex> keys) and the kit's
resolve()/summarize_updates()/choices() helpers are reused so that the label semantics match the kit. Household
names and room sets never overlap the kit's, so no generated state can equal a DI row. Each multi-question home row
is projected to single-question rows (one per sampled question)."""
import copy
import json

from rows import rng, row

from decision_index.suite.build import home_appliance as K

SRC = "synthetic:keel-pro/synth_home.py"
HOMES = ["aster", "basalt", "cobalt", "delta", "ember", "fjord", "granite", "heron", "ivy", "jasper", "kelp", "lagoon", "meadow", "nimbus", "onyx", "pebble", "quill", "raven", "slate", "tundra", "umber", "vale", "wren", "yarrow"]
assert not set(HOMES) & set(K.HOUSEHOLDS)
ROOMS = ["kitchen", "living room", "dining room", "master bedroom", "kids room", "hallway", "attic", "basement", "laundry room", "home office", "sunroom", "loft", "bathroom", "playroom", "library", "balcony", "pantry", "studio", "garden shed", "entryway"]
LIGHT_NAMES = ["Floor Lamp", "Desk Lamp", "Ceiling Light", "Wall Sconce", "Strip Lights", "Night Light", "Track Lights", "Lantern", "Chandelier", "Bedside Lamp", "Accent Light", "Spotlight"]
APPLIANCES = [("Coffee Maker", 900), ("Space Heater", 1500), ("Fan", 45), ("Dehumidifier", 300), ("Humidifier", 40), ("Toaster Oven", 1200), ("TV", 120), ("Printer", 30), ("Electric Blanket", 100), ("Aquarium Pump", 10), ("Monitor", 35), ("Rice Cooker", 700), ("Dishwasher", 1800), ("Iron", 1100), ("Router", 12), ("Game Console", 150), ("Fridge", 150), ("Hair Dryer", 1600)]
SPEAKERS = ["Smart Speaker", "Soundbar", "Radio", "Ceiling Speaker"]
LOCKS = ["Front Door", "Back Door", "Garage Door", "Gate", "Patio Door"]
NOW = ["2026-03-02T07:30:00+01:00", "2025-11-14T18:45:00-05:00", "2026-06-21T12:10:00+09:00", "2025-12-24T21:05:00+00:00", "2026-01-09T06:55:00-08:00"]
STATUSES = ["execute now", "execute available parts now", "schedule for later", "save an automation rule", "ask a clarifying question", "make no change because already satisfied", "reject as unsupported", "block under household policy", "answer a state query"]
STATUS_DESC = {"execute": "execute now", "execute_partial": "execute available parts now", "schedule": "schedule for later", "rule": "save an automation rule", "clarify": "ask a clarifying question", "no_change": "make no change because already satisfied", "unsupported": "reject as unsupported", "blocked": "block under household policy", "query": "answer a state query"}
YES = "yes, this device is in the justified target set"
NO = "no, this device is not in the justified target set"


def make_home(i, r):
    rooms = r.sample(ROOMS, r.randint(3, 6))
    assert rooms not in K.ROOM_SETS
    devices = []
    for room in rooms:
        sl = K.slug(room)
        for j in range(r.randint(1, 2)):
            devices.append({"id": f"{sl}_light" + (f"_{j + 1}" if j else ""), "name": r.choice(LIGHT_NAMES), "room": room, "kind": "light", "available": r.random() > 0.08, "power": r.random() < 0.5, "brightness": r.choice(range(10, 101, 5)), "watts": r.choice([5, 7, 9, 12, 15, 20, 40])})
        for j in range(r.randint(0, 2)):
            name, w = r.choice(APPLIANCES)
            devices.append({"id": f"{sl}_{K.slug(name)}", "name": name, "room": room, "kind": "appliance", "available": r.random() > 0.08, "power": r.random() < 0.5, "watts": w})
    devices = list({d["id"]: d for d in devices}.values())
    tmin = r.choice([5, 10, 15, 16, 17])
    tmax = r.choice([25, 26, 28, 30])
    devices.append({"id": f"{K.slug(rooms[0])}_thermostat", "name": "Thermostat", "room": rooms[0], "kind": "thermostat", "available": True, "power": True, "temperature": r.randint(tmin + 2, tmax - 2), "min_temperature": tmin, "max_temperature": tmax, "watts": 3})
    if r.random() < 0.8:
        devices.append({"id": f"{K.slug(rooms[1])}_speaker", "name": r.choice(SPEAKERS), "room": rooms[1], "kind": "speaker", "available": True, "power": r.random() < 0.5, "volume": r.choice(range(0, 101, 5)), "watts": 15})
    devices.append({"id": f"{K.slug(rooms[-1])}_lock", "name": r.choice(LOCKS), "room": rooms[-1], "kind": "lock", "available": True, "locked": r.random() < 0.5, "watts": 1})
    r.shuffle(devices)
    ids = [d["id"] for d in devices]
    powered = [d["id"] for d in devices if "power" in d and d["kind"] != "thermostat"]
    alias = r.choice(["upstairs", "back room", "front rooms", "quiet area", "east wing"])
    group = r.choice(["evening", "morning", "movie night", "away", "bedtime"])
    zone = r.choice(["downstairs", "ground floor", "common areas"])
    return {"home": HOMES[i % len(HOMES)] + f"-{i}", "now": r.choice(NOW), "outside_temperature": r.randint(-5, 32), "rooms": rooms, "room_aliases": {alias: r.sample(rooms, 2)}, "devices": devices, "groups": {group: r.sample(powered, min(len(powered), r.randint(2, 4))), zone: [d["id"] for d in devices if d["room"] in rooms[: max(2, len(rooms) // 2)]]}, "device_context": r.choice(powered), "policy": {"multi_action": "atomic", "conflict": "last_wins", "allow_partial": False, "security_mode": r.choice(["home", "away", "night"]), "away_unlock": "blocked", "unavailable_action": "blocked"}, "schedules": [], "rules": []}, ids


def low(d):
    return f"{d['name'].lower()} in the {d['room']}"


def pick(r, ds, pred):
    c = [d for d in ds if pred(d)]
    return r.choice(c) if c else None


def scenario(home, name, r):
    ds = home["devices"]
    avail = lambda d: d.get("available", True)
    sw = lambda d: "power" in d and d["kind"] in ("light", "appliance", "speaker") and avail(d)
    therm = next(d for d in ds if d["kind"] == "thermostat")
    lock = next(d for d in ds if d["kind"] == "lock")
    if name == "exact_toggle":
        d = pick(r, ds, sw)
        v = not d["power"]
        req = r.choice(["Please turn {s} the {n}.", "Can you switch {s} the {n}?", "{S} the {n}, thanks.", "I'd like the {n} {s}."]).format(s="on" if v else "off", S="Turn on" if v else "Turn off", n=low(d))
        return {"kind": "execute", "ops": [[d["id"], "power", v]]}, req
    if name == "room_except":
        room = r.choice(home["rooms"])
        lights = [d for d in ds if d["room"] == room and d["kind"] == "light"]
        if len(lights) < 2 or not all(avail(d) for d in lights):
            return None
        keep = r.choice(lights)
        v = r.random() < 0.5
        return {"kind": "execute", "ops": [[d["id"], "power", v] for d in lights if d is not keep]}, f"Switch {'on' if v else 'off'} all the lights in the {room} except the {keep['name'].lower()}."
    if name == "named_group":
        g = next(iter(home["groups"]))
        if not all(avail(K.dev(home, x)) for x in home["groups"][g]):
            return None
        v = r.random() < 0.6
        return {"kind": "execute", "ops": [[x, "power", v] for x in home["groups"][g]]}, r.choice([f"{'Start' if v else 'Stop'} the {g} group.", f"Turn {'on' if v else 'off'} everything in the {g} group."])
    if name == "duplicate_name":
        by = {}
        for d in ds:
            by.setdefault(d["name"], []).append(d)
        dup = [v for v in by.values() if len(v) > 1 and all("power" in d for d in v)]
        if not dup:
            return None
        group = r.choice(dup)
        return {"kind": "clarify", "candidates": [d["id"] for d in group]}, f"Turn {'on' if r.random() < 0.5 else 'off'} the {group[0]['name']}."
    if name == "already_satisfied":
        d = pick(r, ds, sw)
        return {"kind": "no_change", "ops": [[d["id"], "power", d["power"]]]}, r.choice([f"Make sure the {low(d)} is {'on' if d['power'] else 'off'}.", f"Keep the {low(d)} {'on' if d['power'] else 'off'}."])
    if name == "range_reject":
        v = r.choice([therm["max_temperature"] + r.randint(1, 8), therm["min_temperature"] - r.randint(1, 8)])
        return {"kind": "unsupported", "ops": [[therm["id"], "temperature", v]], "reason": "outside supported range"}, f"Set the thermostat to {v}°C."
    if name == "atomic_block":
        a = pick(r, ds, sw)
        b = pick(r, ds, lambda d: "power" in d and d["kind"] in ("light", "appliance") and not avail(d))
        if not a or not b:
            return None
        return {"kind": "blocked", "ops": [[a["id"], "power", True], [b["id"], "power", True]], "reason": "atomic request contains unavailable device"}, f"Turn on the {low(a)} and the {low(b)} together."
    if name == "future_schedule":
        d = pick(r, ds, sw)
        hh, mm = r.randint(0, 23), r.choice([0, 15, 30, 45])
        v = r.random() < 0.5
        h12 = f"{(hh % 12) or 12}:{mm:02d} {'am' if hh < 12 else 'pm'}"
        return {"kind": "schedule", "at": f"{hh:02d}:{mm:02d}", "ops": [[d["id"], "power", v]]}, f"At {h12}, turn {'on' if v else 'off'} the {low(d)}."
    if name == "conditional_rule":
        t = r.randint(0, 30)
        set_to = r.randint(therm["min_temperature"], therm["max_temperature"])
        cond = r.choice(["below", "above"])
        return {"kind": "rule", "condition": ["outside_temperature", cond, t], "ops": [[therm["id"], "temperature", set_to]]}, f"Whenever it's {cond} {t}°C outside, set the thermostat to {set_to}°C."
    if name == "power_filter":
        room = r.choice(home["rooms"])
        th = r.choice([50, 100, 200, 500])
        ts = [d for d in ds if d["room"] == room and d["kind"] == "appliance" and d["watts"] > th]
        if not ts or not all(avail(d) for d in ts):
            return None
        return {"kind": "execute", "ops": [[d["id"], "power", False] for d in ts]}, f"In the {room}, turn off the appliances that draw more than {th} watts."
    if name == "context_pronoun":
        d = K.dev(home, home["device_context"])
        if not avail(d):
            return None
        v = not d["power"]
        return {"kind": "execute", "ops": [[d["id"], "power", v]]}, r.choice([f"Turn it {'on' if v else 'off'} as well.", f"Now switch that one {'on' if v else 'off'}."])
    if name == "missing_device":
        names = {d["name"].lower() for d in ds}
        thing = r.choice([n for n, _ in APPLIANCES if n.lower() not in names] + ["Robot Vacuum", "Sprinkler", "Garage Heater"])
        return {"kind": "clarify", "candidates": []}, f"Start the {thing.lower()} in the {r.choice(home['rooms'])}."
    if name == "relative_level":
        d = pick(r, ds, lambda d: d["kind"] == "light" and avail(d))
        step = r.choice([10, 15, 20, 25, 30])
        up = r.random() < 0.5
        v = min(100, d["brightness"] + step) if up else max(0, d["brightness"] - step)
        return {"kind": "execute", "ops": [[d["id"], "brightness", v]]}, f"Make the {low(d)} {step} points {'brighter' if up else 'dimmer'}."
    if name == "room_alias_ambiguous":
        alias, rooms = next(iter(home["room_aliases"].items()))
        c = [d["id"] for d in ds if d["room"] in rooms and d["kind"] == "light"]
        if len(c) < 2:
            return None
        return {"kind": "clarify", "candidates": c}, f"Turn off the light in the {alias}."
    if name == "last_wins":
        d = pick(r, ds, sw)
        home["policy"]["multi_action"] = "ordered"
        v = r.random() < 0.5
        return {"kind": "execute", "ops": [[d["id"], "power", v], [d["id"], "power", not v]]}, f"Turn the {low(d)} {'on' if v else 'off'}, then {'off' if v else 'on'} again."
    if name == "partial_unavailable":
        a = pick(r, ds, sw)
        b = pick(r, ds, lambda d: "power" in d and d["kind"] in ("light", "appliance") and not avail(d))
        if not a or not b:
            return None
        home["policy"]["allow_partial"] = True
        home["policy"]["multi_action"] = "best_effort"
        return {"kind": "execute_partial", "ops": [[a["id"], "power", True], [b["id"], "power", True]]}, f"Turn on the {low(a)} and the {low(b)}; just do what you can."
    if name == "security_policy":
        home["policy"]["security_mode"] = "away"
        lock["locked"] = True
        return {"kind": "blocked", "ops": [[lock["id"], "locked", False]], "reason": "away mode blocks unlock"}, f"Unlock the {lock['name'].lower()}."
    if name == "ordered_sequence":
        d = pick(r, ds, lambda d: d["kind"] == "light" and avail(d))
        home["policy"]["multi_action"] = "ordered"
        b = r.choice(range(10, 101, 10))
        return {"kind": "execute", "ops": [[d["id"], "power", False], [d["id"], "brightness", b], [d["id"], "power", True]]}, f"Turn off the {low(d)}, set it to {b}%, then turn it back on."
    if name == "group_exception":
        zone = list(home["groups"])[1]
        members = [x for x in home["groups"][zone] if "power" in K.dev(home, x) and K.dev(home, x)["kind"] != "thermostat"]
        if len(members) < 2 or not all(avail(K.dev(home, x)) for x in members):
            return None
        keep = r.choice(members)
        return {"kind": "execute", "ops": [[x, "power", False] for x in members if x != keep]}, f"Turn off the {zone} group but leave the {low(K.dev(home, keep))} alone."
    d = r.choice([therm, lock] + [x for x in ds if x["kind"] == "speaker"])
    prop = {"thermostat": "temperature", "lock": "locked", "speaker": "volume"}[d["kind"]]
    q = {"temperature": "What temperature is the thermostat set to?", "locked": f"Is the {d['name'].lower()} locked right now?", "volume": f"What's the volume on the {d['name'].lower()}?"}[prop]
    return {"kind": "query", "target": d["id"], "property": prop}, q


def make_rows(i, per_home=3):
    r = rng("home", i)
    for _ in range(50):
        home, _ids = make_home(i, r)
        name = K.SCENARIOS[i % len(K.SCENARIOS)] if r.random() < 0.7 else r.choice(K.SCENARIOS)
        out = scenario(home, name, r)
        if out:
            break
    else:
        return []
    spec, request = out
    result = K.resolve(home, spec)
    state = {k: v for k, v in home.items() if k != "home"}
    state["request"] = request
    status_desc = STATUS_DESC[result["status"]]
    qdefs = [("How should the assistant handle the request?", STATUSES, status_desc)]
    targets = set() if result["status"] == "clarify" else set(result["targets"])
    members = [d for d in home["devices"] if d["id"] in targets]
    others = [d for d in home["devices"] if d["id"] not in targets]
    for d in r.sample(members, min(1, len(members))) + r.sample(others, min(1, len(others))):
        qdefs.append((f"Is {d['id']} in the justified device target set for this request?", [YES, NO], YES if d["id"] in targets else NO))
    outcome = K.summarize_updates(result)
    distract = ["no device property changes", "a future schedule is added; device properties do not change yet", "an automation rule is saved; device properties do not change immediately"]
    if result["targets"]:
        did = result["targets"][0]
        distract += [f"{did}.power becomes true", f"{did}.power becomes false"]
    qdefs.append(("What is the concrete immediate outcome after applying the correct handling?", [outcome] + [x for x in distract if x != outcome], outcome))
    probe = r.choice(home["devices"])
    prop = "power" if "power" in probe else "locked" if "locked" in probe else "temperature"
    pval = probe[prop]
    vals = [f"{probe['id']}.{prop} is {json.dumps(pval)}", f"{probe['id']}.{prop} is {json.dumps(not pval) if isinstance(pval, bool) else pval + 1}", "the property is not listed"]
    qdefs.append((f"Before handling the request, what is the listed {prop} state of {probe['name']} in {probe['room']}?", vals, vals[0]))
    for did, prop, value in spec.get("ops", [])[:2]:
        actual = K.dev(result["final"], did).get(prop)
        vals = [json.dumps(actual), json.dumps(value), json.dumps(K.dev(home, did).get(prop)), "not applicable or not listed"]
        qdefs.append((f"Immediately after correct handling, what is {prop} for {did}?", vals, json.dumps(actual)))
    chosen = [qdefs[0]] + r.sample(qdefs[1:], min(per_home - 1, len(qdefs) - 1))
    rows = []
    for pos, (instruction, vals, answer) in enumerate(chosen):
        if len(dict.fromkeys(vals)) < 2:
            continue
        criteria, gold = K.choices(r, vals, answer, f"keelpro:{i}:{pos}")
        rows.append(row(9, SRC, copy.deepcopy(state), {"type": "choice", "instructions": instruction, "criteria": criteria}, gold))
    return rows


def home(cap):
    out, i = [], 0
    while len(out) < cap:
        out.extend(make_rows(i))
        i += 1
    return out[:cap]
