import cmd
from calendar import TextCalendar

from shlex import split

class CalCmd(cmd.Cmd):
    prompt = "Cal ==> "

    def do_month(self, arg):
        """"Print a month’s calendar as returned by formatmonth()."""
        args = split(arg)
        args = [int(arg) for arg in args]
        cal = TextCalendar()
        print(cal.prmonth(*args))

    def complete_month(self, text, line, bidx, eidx):
        months = list(calendar.Month)

    def do_year(self, arg):
        """Print the calendar for an entire year as returned by formatyear()."""
        args = split(arg)
        args = [int(arg) for arg in args]
        cal = TextCalendar()
        print(cal.pryear(*args))

if __name__ == "__main__":
    CalCmd().cmdloop()
