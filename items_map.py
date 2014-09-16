biolabQuestsExternal = ['Friendship Quest', 'Bio Lab Entrance Quest']
namelessIslandQuestsExternal = ['Lost Child Quest', 'Rachel Sanctuary Entrance Quest', 'Veins Siblings Quest', 'Curse of Gaebolg Quest', 'Nameless Island Entrance Quest']
ktullanaxQuestExternal = ['Ice Necklace Quest']
thanatosQuestExternal = ['Thanatos Tower Quest']
sealedShrineQuestExternal = ['Sealed Shrine Quest']
morrocQuestExternal = ['Continental Guard Quest']
gloomQuestExternal = ['Rachel Sanctuary Entrance Quest', 'Lost Child Quest']
niddhoggQuestsExternal = ['Tripatriate Unions Feud', 'Attitude To The New World', 'Ring Of The Wise King', 'New Surroundings', 'Two Tribes', 'Pursuing Rayan Moore', 'Report From The New World', 'Guardian Of Yggsdrasil Step 9', 'Onward To The New World']
EndlessTowerExternal = []

cards_to_coins = { 
  4407 : 20.0, 
  4145 : 20.0,
  4430 : 20.0,
  4367 : 20.0,
  4363 : 12.0,
  4361 : 20.0,
  4357 : 12.0,
  4365 : 20.0,
  4359 : 12.0,
  4419 : 20.0,
  4145 : 20.0,
  4441 : 20.0, 
  4147 : 12.0,
  4408 : 20.0, 
  4407 : 20.0
}

#instance name, median_number, mob_id, mob_name, mob_drop_rate, quests
#added placeholder for ET mvps.  
#added naming and ordering for ET.
instance_mob_item_mapping = [
  ['Sealed Shrine', 5, [(1929, 'Greater Demon Baphomet', [(6004, .15), (2514, .7), (1181, .5), (1181, .01), (2513, .7), (2327, .7), (1466, .9), (4147, .0003)])], sealedShrineQuestExternal],
  ['Niddhoggs Nest', 6, [(2022, 'Nidhoggrs Shadow', [(6091, 1.0), (7444, 1.0), (2610, .5), (1484, .05), (1170, .05), (1417, .05), (2554, .1), (5467, .15)])], niddhoggQuestsExternal],
  ['Ktullanax', 4, [(1779, 'Ktullanux', [(7562, 1.0), (616, .9), (2509, .2), (2111, .2), (617, 1.0), (607, 1.0), (4419, .0003)])], ktullanaxQuestExternal],
  ['Nameless - Beelzebub', 5, [(1874, 'Beelzebub', [(7562, 1.0), (616, .9), (2509, .2), (2111, .2), (617, 1.0), (607, 1.0), (4419, .0003)])], namelessIslandQuestsExternal],
  ['Nameless - Fallen Bishop', 3, [(1871, 'Fallen Bishop Hibram', [(523, 1.0), (1420, .05), (2677, .05), (1422, .05), (985, 1.0), (1614, .2), (18538, .04), (4441, .0003)])], namelessIslandQuestsExternal],
  ['Thanatos', 4, [(1708, 'Memory of Thanatos', [(7444, .3), (2519, .1), (7450, 1.0), (2342, .5), (2412, .5), (2515, .1), (2655, .05), (5377, .1), (5462, .1), (4399, .0003)])], thanatosQuestExternal],
  ['Gloom', 3, [(1768, 'Gloom Under Night', [(7566, 1.0), (7023, 1.0), (7022, .6), (616, 1.0), (2513, .1), (1377, .01), (5306, .027), (4408, .0003)])], gloomQuestExternal],
  ['Morroc', 6, [(1917, 'Wounded Morroc', [(5808, .075), (2374, .1), (2375, .12), (2433, .25), (7799, 1.0), (7798, 1.0)])], morrocQuestExternal],
  ['Valkyrie Randgris', 6, [(1751, 'Valkyrie Randgris', [(7510, 1.0), (2357, .12), (2524, .15), (2421, .3), (2229, .5), (7024, .75), (2115, .16), (4407, .0003)])], []],
  ['Bio - Sniper', 5, [(1650, 'Sniper Cecil', [(1228, .35), (1236, .35), (617, 1.0), (1234, .15), (1237, .35), (1720, .15), (1724, .25), (4367, .0003)])], biolabQuestsExternal],
  ['Bio - High Priest', 5, [(1649, 'High Priest Margaretha', [(1814, .35), (2615, .25), (2513, .9), (1557, .35), (1527, .35), (1528, .25), (1560, .35), (4363, .0003)])], biolabQuestsExternal],
  ['Bio - High Wizard', 5, [(1651, 'High Wizard Kathryne', [(1241, .35), (1242, .35), (2616, .9), (2343, .25), (2513, .25), (1618, .3), (2319, .35), (4365, .0003)])], biolabQuestsExternal],
  ['Bio - Whitesmith', 5, [(1648, 'Whitesmith Howard', [(1138, .35), (1140, .25), (2318, .9), (1365, .35), (1364, .35), (1369, .25), (1368, .35), (4361, .0003)])], biolabQuestsExternal],
  ['Bio - Assassin Cross', 5, [(1647, 'Assassin Cross Eremes', [(1234, .15), (1230, .15), (2319, .9), (1233, .35), (1232, .35), (1265, .35), (13002, .35), (4359, .0003)])], biolabQuestsExternal],
  ['Bio - Lord Knight', 5, [(1646, 'Lord Knight Seyren', [(1132, .25), (2342, .35), (2412, .9), (1470, .35), (1469, .3), (1166, .25), (1415, .15), (4357, .0003)])], biolabQuestsExternal],
  ['Endless Tower', 10, [\
  (1086, '5 - Golden Thief Bug', [(969, .30), (1524, .015), (2246, .025), (10016, .15), (714, .09), (985, .60), (984, .45), (4128, .0003), (2610, .20), (701, .10)]), \
  (1059, '10 - Mistress', [(1413, .015), (518, 1.0), (2249, .025), (616, .30), (7018, .03), (985, 1), (16001, .01), (4132, .0003), (996, .15), (526, .40), (722, .30)]), \
  (1147, '15 - Maya', [(10006, .15), (2615, .02), (2234, .02), (639, .15), (7020, .03), (985, 1.0), (2005, .01), (8518, .027), (4146, .0003), (730, .20), (603, .30), (617, .20)]), \
  (1159, '15 - Phreeoni', [(1223, .05), (1236, .015), (1014, 1.0), (2288, .03), (985, .87), (13047, .01), (8522, .027), (4121, .0003), (1008, .05), (730, .10), (1000, .40)]), \
  (1112, '20 - Drake', [(1127, .06), (1135, .015), (1128, .04), (5019, .035), (985, .096), (1189, .01), (5417, .024), (1127, .06)]), \
  (1150, '25 - Moonlight Flower', [(1477, .05), (1234, .01), (1525, .015), (10008, .15), (638, .195), (985, .78), (1648, .01), (5360, .027), (4131, .0003)]), \
  (1630, '30 - Bacsojin', [(1020, 1.0), (603, 1.0), (12395, .015), (7165, .90), (7166, .30), (2700, .01), (2234, .001), (5464, .027), (4372,.0003)]), \
  (1312, '35 - Turtle General', [(1306, .0005), (7480, .006), (1417, .0009), (7070, 1.0), (1141, .008), (658, .0003), (5611, .001), (4305, .0003), (967, .55), (607, .15), (617, .20)]), \
  (1542, '40 - Incantation Samurai', [(607, 1.0), (985, 1.0), (999, 1.0), (1165, .0006), (1235, .024), (4263, .0003), (5096, .15), (13303, 1.0), (607, 1.0), (608, 1.0), (985, 1.0)]), \
  (1038, '45 - Osiris', [(617, .60), (1232, .015), (2235, .02), (1255, .06), (1009, .30), (5053, .015), (1285, .01), (4144, .0003), (603, .40), (608, .30), (751, .05)]), \
  (1511, '50 - Amon Ra', [(5053, .015), (2615, .005), (7211, 1.0), (985, 1.0), (616, .12), (1552, .001), (607, .90), (4236, .0003), (607, .55), (608, .35), (732, .55)]), \
  (1157, '50 - Pharaoh', [(7113, 1.0), (7114, .75), (1136, .01), (2327, .015), (5002, .05), (1552, .03), (1231, .008), (4148, .0003), (607, .55), (526, .50), (732, .50)]), \
  (1418, '55 - Evil Snake Lord', [(7169, 1.0), (10020, 1.0), (1471, .008), (5012, .008), (1474, .05), (7226, .27), (661, .60), (5364, .027), (4330, .0003 ), (607, .55), (608, .35), (985, .55)]), \
  (1658, '60 - General Egnigem Cenia', [(1162, .10), (644, 1.0), (603, 1.0), (1167, .10), (2320, .10), (2406, .10), (1130, .10), (4352, .0003), (617, .55), (603, .50), (732, .20)]), \
  (1046, '60 - Doppelganger', [(2317, .025), (1162, .022), (1168, .015), (2258, .035), (1411, .055), (985, 1.0), (984, .81), (4142, .0003)]), \
  (1785, '65 - Atroce', [(7563, 1.0), (608, .30), (2621, .02), (617, 1.0), (607, 1.0), (5123, .01), (1175, .01), (4425, .0003), (607, .55), (617, .50), (617, .50)]), \
  (1087, '70 - Orc Hero', [(968, 1.0), (10018, .15), (1366, .015), (2106, .025), (1124, .10), (985, 1.0), (1387, .01), (4143, .0003)]), \
  (1190, '70 - Orc Lord', [(1363, .04), (2621, .04), (5007, .04), (1371, .04), (617, .30), (985, 1.0), (16000, .01), (4135, .0003), (968, .55), (617, .20)]), \
  (1272, '75 - Dark Lord', [(1615, .08), (5017, .055), (1237, .03), (2334, .03), (2507, .01), (985, 1.0), (2004, .01), (4168, .0003), (7005, .60), (5093, .05), (617, .20)]), \
  (1039, '75 - Baphomet', [(1466, .04), (2256, .03), (1476, .005), (714, .15), (5160, .001), (985, 1.0), (984, 1.0), (4147, .0003)]), \
  (1871, '80 - Fallen Bishop Hibram', [(523, 1.0), (1420, .05), (2677, .05), (1422, .05), (985, 1.0), (1614, .20), (18538, .04), (4441, .0003), (607, .55), (617, .50), (617, .50)]), \
  (1832, '85 - Ifrit', [(994, 1.0), (2677, .30), (12103, .0999), (13017, .005), (1471, .20), (1133, .20), (2345, .01), (5420, .10), (4430, .0003), (603, .55), (617, .50), (616, .20)]), \
  (1751, '90 - Valkyrie Randgris', [(7510, 1.0), (2357, .12), (2524, .15), (2421, .3), (2229, .5), (7024, .75), (2115, .16), (4407, .0003), (617, .55), (603, .50), (616, .20)]), \
  (1874, '95 - Beelzebub', [(7754, 1.0), (2423, .20), (1565, .20), (2000, .20), (2702, .20), (985, 1.0), (742, 1.0), (4145, .0003)]), \
  (1957, '100 - Entweihen Crothen', [(1636, .90), (1631, .90), (2513, .90), (1624, .90), (616, 1.0), (1618, .90), (7291, 1.0)]), \
  (1956, '101 - Naght Sieger', [(13412, .5), (13413, .5), (2542, .5), (5017, .90), (616, 1.0), (2514, .9), (7294, 1.0)]) \
  ], EndlessTowerExternal]
]  

#mobs
#2022 - nidd
#1751 - valk
#1832 - ifrit
#1874 - beelzebub
#1956 - naght sieger
#1957 - Entweihen Crothen
#1650 - Sniper Cecil
#1649 - High Priest Margaretha
#1651 - High Wizard Kathryne
#1648 - Whitesmith Howard
#1647 - Assassin Cross Eremes
#1646 - Lord Knight Seyren

mobs_in_run = {
  'Niddhogg' : [2022],
  'ET' : [1751, 1832, 1874, 1956, 1957],
  'Bio' : [1650, 1649, 1651, 1648, 1647, 1646]
}

median_party_size = {
  'Niddhogg' : 4.0,
  'ET' : 9.0,
  'Bio' : 7.0  
}

mob_drop_rate = {
  2022 : [(6091, 1.0), (7444, 1.0), (2610, .5), (1484, .05), (1170, .05), (1417, .05), (2554, .1), (5467, .15)],
  1751 : [(7510, 1.0), (2357, .12), (2524, .15), (2421, .3), (2229, .5), (7024, .75), (2115, .16), (4407, .0003)],
  1832 : [(994, 1.0), (2677, .3), (12103, .0999), (13017, .005), (1471, .2), (1133, .2), (2345, .01), (5420, .1), (4430, .0003)],
  1874 : [(7754, 1.0), (2423, .2), (1565, .2), (2000, .2), (2702, .2), (985, 1.0), (742, 1.0), (4145, .0003)],
  1956 : [(13412, .5), (13413, .5), (2542, .5), (5017, .9), (616, 1.0), (2514, .9), (7294, 1.0)],
  1957 : [(1636, 1.0), (1631, 1.0), (2513, 1.0), (1624, 1.0), (616, 1.0), (1618, 1.0), (7291, 1.0)],
  1650 : [(1228, .35), (1236, .35), (617, 1.0), (1234, .15), (1237, .35), (1720, .15), (1724, .25), (4367, .0003)],
  1649 : [(1814, .35), (2615, .25), (2513, .9), (1557, .35), (1527, .35), (1528, .25), (1560, .35), (4363, .0003)],
  1651 : [(1241, .35), (1242, .35), (2616, .9), (2343, .25), (2513, .25), (1618, .3), (2319, .35), (4365, .0003)],
  1648 : [(1138, .35), (1140, .25), (2318, .9), (1365, .35), (1364, .35), (1369, .25), (1368, .35), (4361, .0003)],
  1647 : [(1234, .15), (1230, .15), (2319, .9), (1233, .35), (1232, .35), (1265, .35), (13002, .35), (4359, .0003)],
  1646 : [(1132, .25), (2342, .35), (2412, .9), (1470, .35), (1469, .3), (1166, .25), (1415, .15), (4357, .0003)]
}

search_items = { 
  607  : "Yggdrasil Berry",
  7321 : "Crystal Fragment",
  604  : "Dead Branch",
  578  : "Strawberry",
  582  : "Orange",
  12010 : "Wind Arrow Quiver",
  12012 : "Crystal Arrow Quiver",
  12013 : "Shadow Arrow Quiver",
  12014 : "Immaterial Arrow Quiver",
  2537 : "Diablos Manteau [1]",
  2374 : "Diablos Robe [1]",
  2375 : "Diablos Armor [1]",
  2433 : "Diablos Boots [1]",
  2729 : "Diablos Ring [1]",
  5808 : "Dark Bashilrium [1]",
  4054 : "Angeling Card",
  4045 : "Horn Card",
  4047 : "Ghostring Card",
  4276 : "Lord of Death Card",
  4105 : "Marc Card",
  4095 : "Marse Card",
  4141 : "Evil Druid Card",
  4168 : "Dark Lord Card",
  4169 : "Dark Illusion Card", 
  4408 : "Gloom Under Night Card",
  4419 : "Ktullanux Card",
  8049 : "Sleipnir [1]",
  1169 : "Executioner",
  1179 : "Executioner [1]",
  4253 : "Alice Card",
  4058 : "Thara Frog Card",
  4123 : "Eddga Card",
  1166 : "Dragon Slayer",
  1180 : "Dragon Slayer [2]",
  1188 : "Veteran Sword",
  4142 : "Doppelganger Card",
  4147 : "Baphomet Card",
  4520 : "Leak Card",
  8900 : "Talon Coin", 
  6091 : "Red Scale", 
  7444 : "Treasure Box", 
  2610 : "Gold Ring", 
  1484 : "Carled", 
  1170 : "Katzbalger", 
  2554 : "Nydhorgg's Shadow Garb", 
  1417 : "Pole Axe", 
  5467 : "Helm of Dragon", 
  4407 : "Valkyrie Randgris Card", 
  2357 : "Valkyrja's Armor", 
  2524 : "Valkyrja's Manteau", 
  2421 : "Valkyrja's Shoes", 
  2229 : "Helm", 
  7024 : "Bloody Edge", 
  2115 : "Valkyrja's Shield", 
  7510 : "Valhalla's Flower",
  7754 : "Broken Crown",
  2423 : "Variant Shoes", 
  1565 : "Book of the Dead",
  2000 : "Staff of Destruction",
  2702 : "Horn of the Buffalo",
  985 : "Elunium",
  742 : "Chonchon Doll",
  4145 : "Berzebub Card",
  994 : "Flame Heart",
  2677 : "Spiritual Ring",
  12103 : "Bloody Branch",
  13017 : "Ice Pick [1]",
  1471 : "Hellfire",
  1133 : "Fireblend",
  2345 : "Lucius's Fierce Armor of Volcano [1]",
  5420 : "Mask Of Ifrit",
  4430 : "Ifrit Card",
  13412 : "Naght Seiger Twin Blade(B) [3]",
  13413 : "Naght Seiger Twin Blade(R) [3]",
  2542 : "Naght Seiger Flame Manteau [1]",
  5017 : "Bone Helm",
  616 : "Old Card Album",
  2514 : "Pauldron [1]",
  7294 : "Turquoise",
  1636 : "Dark Thorn Staff",
  1631 : "Holy Stick [1]",
  2513 : "Heavenly Maiden Robe [1]", 
  1624 : "Lich's Bone Wand [2]",
  1618 : "Survivor's Rod [1]",
  7291 : "Agate",
  1228 : "Combat Knife",
  1236 : "Sucsamad",
  617 : "Old Purple Box",
  1234 : "Moonlight Dagger",
  1237 : "Grimtooth",
  1720 : "Rudra Bow",
  1724 : "Dragon Wing",
  4367 : "Sniper Card",
  1814 : "Berserk",
  2615 : "Safety Ring",
  1557 : "Book of the Apocalypse",
  1527 : "Quadrille",
  1528 : "Grand Cross",
  1560 : "Sage's Diary [2]",
  4363 : "High Priest Card",
  1138 : "Mysteltainn",
  1140 : "Byeollungum",
  2318 : "Lord's Clothes [1]",
  1365 : "Sabbath", 
  1364 : "Great Axe",
  1369 : "Guillotine",
  1368 : "Tomahawk",
  4361 : "Whitesmith Card",
  1132 : "Edge",
  2342 : "Legion Plate Armor [1]",
  2412 : "Greaves [1]",
  1470 : "Brionac",
  1469 : "Longinus's Spear",
  1166 : "Dragon Slayer",
  1415 : "Brocca",
  4357 : "Lord Knight Card",
  1241 : "Cursed Dagger",
  1242 : "Dagger of Counter",
  2616 : "Critical Ring",
  2343 : "Robe of Cast",
  1618 : "Survivor's Rod [1]",
  2319 : "Glittering Jacket [1]",
  4365 : "High Wizard Card",
  1230 : "Ice Pick",
  1233 : "Exorciser",
  1232 : "Assassin Dagger",
  1265 : "Bloody Roar",
  13002 : "Ginnungagap",
  4359 : "Assassin Cross Card",
  7799 : "Crystal Of Darkness",
  7798 : "Fragment Of Darkness"
}

test_file = "requests_results_sell.html"
test_items = { 
  8900 : "Talon Coin", 
  2554 : "Nydhorgg's Shadow Garb" 
}