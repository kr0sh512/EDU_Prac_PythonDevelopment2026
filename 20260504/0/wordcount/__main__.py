import gettext
import locale

from wordcount import PATH

locale.setlocale(locale.LC_ALL, '')
translation = gettext.translation('wordcount', PATH, fallback=True)
ngettext = translation.ngettext

words = input().split()
n = len(words)
print(ngettext('Entered {} word', 'Entered {} words', n).format(n))
