import re

file = open('source.md', 'r')
lines = file.readlines()

pattern = re.compile(
    '^(?P<indent>`\s*`)?(?P<code>[0-9]+)\s+(?P<name>[^0-9]*)\s+(?P<born>[0-9]+)\s*(?P<date2>[0-9]+)?\s*(?P<date3>[0-9]+)?\s*(((?P<spouse>[^0-9]*)(\s\((?P<code2>[0-9]*)\))?)(\s+(?P<born2>[0-9]+)?\s*(?P<dead2>[0-9]+)?)?)?$')

namePattern = re.compile('^(?P<first>.*)\s(?P<last>[A-Z]?.?[A-Z][A-Z]+.*)$')

nicknamePattern = re.compile('(?P<first>.*)\s«(?P<nick>.*)»')

class Event:
    def __init__(self):
        self.indented = False
        self.code = ""
        self.name = ""
        self.member =  False
        self.female = False
        self.born = None
        self.dead = None
        self.married = None
        self.spouse = False
        self.divorced = False
        self.cross = ""

    def __str__(self):
        return self.code + ": "+self.name+" / " + ("M" if not self.female else "F") + " " + self.born + "-"+(self.dead if self.dead else "") + (" ("+self.married+")" if self.married else "")+("." if self.divorced else "")+(" ["+self.cross+"]" if self.cross else "")

def attributes(event, name):
    event.member = "**" in name
    event.female = "***" in name or (
        "*" in name and not "**" in name)
    event.divorced = "(" in name

def events():
    for line in lines:
        m = pattern.match(line.replace("----", "0000").replace("??", "0000"))
        if m:
            main = Event()
            main.name = m.group('name').replace("*", "").strip()
            indented = m.group('indent') is not None
            main.indented = indented
            attributes(main, m.group('name'))
            main.born = m.group('born')
            if not indented or len(m.group('code')) < 4:
                main.code = m.group('code')
                if m.group('spouse'):
                    spouse = Event()
                    spouse.spouse = True
                    spouse.name = m.group('spouse').replace(
                        "*", "").replace("(", "").replace(")", "").strip()
                    spouse.born = m.group('born2')
                    spouse.dead = m.group('dead2')
                    if m.group('code2'):
                        spouse.cross = m.group('code2')
                    attributes(spouse, m.group('spouse'))
                    if m.group("date3"):
                        main.dead = m.group("date2")
                        spouse.married = m.group("date3")
                    else:
                        spouse.married = m.group("date2")
                    yield main
                    yield spouse
                else:
                    if m.group("date2"):
                        main.dead = m.group("date2")
                    yield main
            else:
                # additional spouse
                main.married = m.group('code')
                main.spouse = True
                if m.group("date2"):
                    main.dead = m.group("date2")
                yield main

def normalized():
    last = None
    current = None
    spouse = 1
    for i in events():
        if current:
            if not i.code or i.code == "":
                i.code = current.code + ((spouse-1)* "0")
                spouse += 1
            else:
                current = i
                spouse = 1
                if i.indented:
                    i.code = last[:-1] + i.code
                else:
                    last = i.code
        else:
            current = i
            last = current.code
        yield i

def records():
    for i in normalized():
        if i.spouse and not i.cross and not namePattern.match(i.name):
            continue
        if not i.cross:
            main = not i.spouse
            prefix = "I" if main else "S"

            s = f'0 @{prefix}{i.code.rjust(4, "0")}@ INDI\n'
            s += f'1 NAME\n'
            if main:
                m = nicknamePattern.match(i.name)
                if m:
                    s += f'2 GIVN {m.group("first")}\n'
                    s += f'2 NICK {m.group("nick")}\n'
                else:
                    s += f'2 GIVN {i.name}\n'
                s += f'2 SURN Bovet\n'
                if len(i.code) > 1:
                    s += f'1 FAMC @F{i.code[:-1].rjust(4, "0")}@\n'
            else:
                m = namePattern.match(i.name)
                if m:
                    first = m.group('first')
                    last = m.group('last').title().replace("’O", "’o")
                    particle = first.lower().strip().split(' ')[-1]
                    if particle in [ 'de', 'du', 'von', 'van' ]:
                        first = first[0:-len(particle)]
                        if "du BOIS" in first:
                            first = first.replace("du BOIS", "")
                            last = "Bois "+last
                            particle = "du"
                        s += f'2 SPFX {particle}\n'
                    if "GORDILLO" in first:
                        first = first.replace("GORDILLO", "")
                        last = "Gordillo "+last
                    s += f'2 SURN {last}\n'
                    m = nicknamePattern.match(first)
                    if m:
                        s += f'2 GIVN {m.group("first")}\n'
                        s += f'2 NICK {m.group("nick")}\n'
                    else:
                        s += f'2 GIVN {first}\n'

            if i.female:
                s += f'1 SEX F\n'
            else:
                s += f'1 SEX M\n'

            if i.born:
                s += f'1 BIRT\n'
                if i.born != '0000':
                    s += f'2 DATE {i.born}\n'
            if i.dead:
                s += f'1 DEAT\n'
                if i.dead != '0000':
                    s += f'2 DATE {i.dead}\n'

            yield s

        if not main or i.cross:
            if i.cross:
                wife = i.cross
            else:
                wife = i.code

            if not i.female or i.cross:
                prefix = "I"
            else:
                prefix = "S"

            s = f'0 @F{i.code.rjust(4, "0")}@ FAM\n'
            s += "1 HUSB " + ("@I"+re.sub("0+$", "", i.code).rjust(4,
                                                                 "0")+"@" if i.female else "@S"+i.code.rjust(4, "0")+"@")+"\n"
            s += "1 WIFE " + ("@"+prefix+re.sub("0+$", "", wife).rjust(4,
                                                                 "0")+"@" if not i.female else "@"+prefix+wife.rjust(4, "0")+"@")+"\n"
            s += f'1 MARR\n'
            if i.married and i.married != '0000':
                s += f'2 DATE {i.married}\n'
            if i.divorced:
                s += f'1 DIV\n'
            yield s


#
#l = sorted(list(normalized()), key=lambda i: str(i.code.split('.')[0].ljust(32,"0")))
print('''0 HEAD
1 GEDC
2 VERS 5.5.5
2 FORM LINEAGE-LINKED
3 VERS 5.5.5
1 CHAR UTF-8
1 SOUR gedcom.org
0 @U@ SUBM
1 NAME gedcom.org
''', end='')
for i in records():
    print(i, end='')
print("0 TRLR")




