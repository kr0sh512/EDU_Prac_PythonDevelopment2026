def init_locale():
    import locale
    import gettext

    global _, ngettext

    locale.setlocale(locale.LC_ALL, locale.getlocale())
    translation = gettext.translation("wordcount", "po", fallback=True)
    translation = gettext.translation("wordcount", "po", fallback=True)
    _, ngettext = translation.gettext, translation.ngettext


init_locale()

words = input().split()
N = len(words)
# print(_(f"Entered {N} word(s)"))
print(ngettext("Entered {} word", "Entered {} words", N).format(N))
