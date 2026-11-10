import re

# Example email content
email_text = """
AbsoluteCREW: https://app.crewplanner.com\r\n\r\n# Je bent ingepland op 3 shiften\r\n\r\nBevestig deze shiften alstublieft. Meer informatie vind je in je agenda.\r\n\r\nIngepland op\r\n\r\nvr  5 juli 2024 | 15:00 - 23:00\r\n\r\nHulpkelner 202-205 CAT. II bij Auberge du Pêcheur\r\n\r\nPontstraat 41, 9831 Sint-Martens-Latem, Belgium\r\n\r\nMeer Informatie\r\nBevestig shift\r\n\r\nAls u op dat moment niet beschikbaar bent, dien een intrekking in.\r\n\r\nza  6 juli 2024 | 12:00 - 18:00\r\n\r\nHulpkelner 202-205 CAT. II bij Auberge du Pêcheur\r\n\r\nPontstraat 41, 9831 Sint-Martens-Latem, Belgium\r\n\r\nMeer Informatie\r\nBevestig shift\r\n\r\nAls u op dat moment niet beschikbaar bent, dien een intrekking in.\r\n\r\nza  6 juli 2024 | 18:00 - 01:00\r\n\r\nHulpkelner 202-205 CAT. II bij Auberge du Pêcheur\r\n\r\nPontstraat 41, 9831 Sint-Martens-Latem, Belgium\r\n\r\nMeer Informatie\r\nBevestig shift\r\n\r\nAls u op dat moment niet beschikbaar bent, dien een intrekking in.\r\n\r\nMet vriendelijke groeten,\r\nAbsoluteCREW\r\n\r\n© 2024 AbsoluteCREW. All rights reserved.\r\n
"""

# General pattern matching any two letters followed by a date and time
pattern = r"\r\n(..) +(\d{1,2} \w+ \d{4}) \| (\d{2}:\d{2} - \d{2}:\d{2})\r\n"

matches = re.findall(pattern, email_text)

print(matches)

# Display the matches
for match in matches:
    print(f"Day: {match[0]}, Date: {match[1]}, Time: {match[2]}")
