from unittest import TestCase
import os
import subprocess

import testdata

from captain import Script, ScriptArg, echo


class TestScript(object):

    @property
    def instance(self):
        return Script(self)

    @classmethod
    def create_instance(cls, *args, **kwargs):
        script_path = cls(*args, **kwargs)
        return script_path.instance

    def __init__(self, body, fname=''):
        self.body = body
        if not isinstance(body, basestring):
            self.body = "\n".join(body)

        self.cwd = testdata.create_dir()

        if not fname:
            fname = "{}/{}.py".format(testdata.get_ascii(5), testdata.get_ascii(5))

        self.path = testdata.create_file(
            fname,
            self.body,
            self.cwd
        )

    def __str__(self):
        return self.path

    def run(self, arg_str=''):
        pwd = os.path.dirname(__file__)
        cmd_env = os.environ.copy()
        cmd_env['PYTHONPATH'] = pwd + os.pathsep + cmd_env.get('PYTHONPATH', '')

        cmd = "python -m captain {} {}".format(self.path, arg_str)

        r = ''
        try:
            r = subprocess.check_output(
                cmd,
                shell=True,
                stderr=subprocess.STDOUT,
                cwd=self.cwd,
                env=cmd_env
            ).rstrip()

        except subprocess.CalledProcessError, e:
            raise RuntimeError("cmd returned {} with output: {}".format(e.returncode, e.output))

        return r


class EchoTest(TestCase):
    def setUp(self):
        echo.quiet = False

    def test_non_string(self):
        a = range(5)
        echo.out(a)

    def test_blank_bar(self):
        echo.out("no args, should be one Newline")
        echo.blank()
        echo.bar()

        echo.out("passed in 5")
        echo.blank(5)
        echo.bar('=', 5)

    def test_echo_logging(self):
        """make sure you don't get double echoing when echo is imported before other
        set up logging"""
        script = TestScript(
            [
                "#!/usr/bin/env python",
                "import sys",
                "import logging",
                "rl = logging.getLogger()",
                "log_handler = logging.StreamHandler(stream=sys.stderr)",
                "log_formatter = logging.Formatter('[%(asctime)s] %(message)s', '%m-%dT%H:%M:%S')",
                "log_handler.setFormatter(log_formatter)",
                "rl.addHandler(log_handler)",
                "from captain import echo",
                "",
                "def main():",
                "  echo.out('gotcha')",
                "  return 0"
            ]
        )

        r = script.run()
        self.assertEqual(1, r.count("gotcha"))




class CaptainTest(TestCase):
    def test_raised_exception(self):
        """I want to make sure exception handling is handled correctly"""
        script = TestScript([
            "#!/usr/bin/env python",
            "def main():",
            "  raise ValueError('boom_error')",
            "  return 0"
        ])

        with self.assertRaisesRegexp(RuntimeError, 'returned 1 with output: boom_error') as e:
            r = script.run()

    def test_init_module(self):
        script = TestScript(
            [
                "#!/usr/bin/env python",
                "def main():",
                "  '''the description for foo module'''",
                "  print 'foo/__init__'",
                "  return 0"
            ],
            'foo/__init__.py'
        )

        script.path = 'foo'
        r = script.run()
        self.assertRegexpMatches(r, 'foo/__init__')

        script = TestScript(
            [
                "#!/usr/bin/env python",
                "def main():",
                "  '''the description for foo module'''",
                "  print 'foo/__main__'",
                "  return 0"
            ],
            'foo/__main__.py'
        )

        script.path = 'foo'
        r = script.run()
        self.assertRegexpMatches(r, 'foo/__main__')

        script = TestScript(
            [
                "#!/usr/bin/env python",
                "def main():",
                "  '''the description for foo module'''",
                "  return 0"
            ],
            'foo/bar.py'
        )

        script.path = 'foo'
        with self.assertRaises(RuntimeError):
            r = script.run()

    def test_list(self):
        script = TestScript([""])
        cwd = script.cwd
        testdata.create_files(
            {
                'foo/bar.py': "\n".join([
                    "#!/usr/bin/env python",
                    "def main():",
                    "  '''the description for bar'''",
                    "  return 0"
                ]),
                'che.py': "\n".join([
                    "#!/usr/bin/env python",
                    "def main(): return 0"
                ]),
                'bar/boo.py': "\n".join([
                    "def main():",
                    "  '''the description for boo'''",
                    "  return 0"
                ]),
                'bar/baz.py': "\n".join([
                    "#!/usr/bin/env python",
                    "if __name__ == u'__main__': pass"
                ]),
                'mod1/__init__.py': "\n".join([
                    "#!/usr/bin/env python",
                    "def main():",
                    "  '''the description for mod1'''",
                    "  return 0"
                ]),
                'mod2/__main__.py': "\n".join([
                    "#!/usr/bin/env python",
                    "def main():",
                    "  '''the description for mod1'''",
                    "  return 0"
                ])
            },
            cwd
        )

        script.path = ''
        r = script.run()
        self.assertTrue('che.py' in r)
        self.assertTrue('foo/bar.py' in r)
        self.assertFalse('bar/boo.py' in r)
        self.assertFalse('bar/baz.py' in r)

        self.assertTrue('mod1' in r)
        self.assertFalse('__init__' in r)
        self.assertTrue('mod2' in r)
        self.assertFalse('__main__' in r)

    def test_help(self):
        script = TestScript([
            "#!/usr/bin/env python",
            "def main(foo=int, bar=0, *args, **kwargs):",
            "  return 0"
        ])
        r = script.run("--help")
        self.assertTrue(os.path.basename(script.path) in r)
        self.assertTrue('foo' in r)
        self.assertTrue('bar' in r)
        self.assertTrue('args' in r)


    def test_run_script(self):
        script = TestScript([
            "#!/usr/bin/env python",
            "def main(foo, bar=0, *args, **kwargs):",
            "  print args[0], kwargs['che']",
            "  return 0"
        ])
        r = script.run("--foo=1 --che=oh_yeah awesome")
        self.assertEqual('awesome oh_yeah', r)

        script = TestScript([
            "#!/usr/bin/env python",
            "def main(foo, bar=0, *args):",
            "  print args[0]",
            "  return 0"
        ])
        r = script.run("--foo=1 awesome")
        self.assertEqual('awesome', r)

        script = TestScript([
            "#!/usr/bin/env python",
            "def main(foo=int, *args):",
            "  print args[0]",
            "  return 0"
        ])
        r = script.run("--foo=1 awesome")
        self.assertEqual('awesome', r)

        script = TestScript([
            "#!/usr/bin/env python",
            "def main(foo=int, bar=int):",
            "  print 'foo'",
            "  return 0"
        ])
        r = script.run("--foo=1 --bar=2")
        self.assertEqual('foo', r)

        script = TestScript([
            "def main(*args, **kwargs):",
            "  return 0"
        ])

        with self.assertRaises(RuntimeError):
            script.run()


class ScriptArgTest(TestCase):
    def test_default(self):
        s = ScriptArg('foo')
        s.set_default(True)
        self.assertTrue(s.default)


class ArgTest(TestCase):
    def test_help(self):

        script_path = TestScript("""#!/usr/bin/env python

from captain import echo
from captain.decorators import arg 


@arg('--foo', '-f')
@arg('arg', metavar='ARG')
def main(**kargs):
    '''this is the help description'''
    print args, kwargs
    return 0
""")

        r = script_path.run('--help')

    def test_decorator(self):
        script_path = TestScript([
            "#!/usr/bin/env python",
            "from captain.decorators import arg",
            "@arg('--foo', default=True)",
            "@arg('--bar', '-b', default='bar')",
            "@arg('--boom', default='boom')",
            "@arg('a')",
            "def main(foo, bar, che=1, baz=2, *args, **kwargs):",
            "  print kwargs['a']",
            "  return 0"
        ])
        s = script_path.instance
        parser = s.parser
        #pout.v(s.arg_info)

        a = "aaaaaaaa"
        r = script_path.run(a)
        self.assertTrue(a in r)


class ScriptTest(TestCase):
    def test_parser(self):
        script_path = TestScript([
            "#!/usr/bin/env python",
            "def main(foo, bar, che=1, baz=2, *args, **kwargs):",
            "  return 0"
        ])
        s = Script(script_path)

        s.parser

    def test_parse(self):
        script_path = TestScript([
            "#!/usr/bin/env python",
            "def main(*args, **kwargs):",
            "  return 0"
        ])
        s = Script(script_path)
        s.parse()
        self.assertEqual('', s.description)

        script_path = TestScript([
            "#!/usr/bin/env python",
            "def main(*args, **kwargs):",
            "  '''this is the description'''",
            "  return 0"
        ])
        s = Script(script_path)
        s.parse()
        self.assertEqual('this is the description', s.description)

    def test_scripts(self):
        with self.assertRaises(IOError):
            s = Script("this/is/a/bogus/path")

        script_path = TestScript([
            "def main(*args, **kwargs):",
            "  return 0"
        ])

        s = Script(script_path)

    def test_is_cli(self):
        script_path = TestScript([
            "def main(*args, **kwargs):",
            "  return 0"
        ])

        s = Script(script_path)
        self.assertFalse(s.is_cli())

        script_path = TestScript([
            "#!/usr/bin/env python",
            "",
            "# another python comment"
        ])

        s = Script(script_path)
        self.assertFalse(s.is_cli())

        script_path = TestScript([
            "#!/usr/bin/env python",
            "def main(*args, **kwargs):",
            "  return 0"
        ])
        s = Script(script_path)
        self.assertTrue(s.is_cli())

    def test_parse_bad(self):
        """makes sure bad input is caught in parsing"""
        tests = [
            ("foo=int", ''),
            ("foo=[int]", ''),
            ("foo=[1, 2]", '--foo=3'),
        ]

        for test_in, test_out in tests:
            s = TestScript([
                "#!/usr/bin/env python",
                "def main({}):".format(test_in),
                "  return 0"
            ])

            with self.assertRaises(RuntimeError):
                s.run(test_out)

    def test_parse_good(self):
        tests = [
            ("foo=[1, 2]", '--foo=2', dict(foo=2)),
            (
                "count=1, dry_run=False, matches_per=5, match_all=False, testing=False",
                '--match-all --testing',
                dict(count=1, dry_run=False, matches_per=5, match_all=True, testing=True)
            ),
            ("foo, bar=0, *args, **kwargs", "--foo=1 --che=oh_yeah awesome", dict(foo='1', bar=0)),
            ("foo=baboom", '--foo=5', dict(foo=5)),
            ("foo=int", '--foo=5', dict(foo=5)),
            ("foo=1.0", '--foo=5.0', dict(foo=5.0)),
            ("foo=set()", '--foo=5', dict(foo=['5'])),
            ("foo=set([1, 2])", '--foo=1', dict(foo=1)),
            ("*args", '1 2', dict(args=['1', '2'])),
            ("foo=[int]", '--foo=5 --foo=6', dict(foo=[5, 6])),
            ("foo=[]", '--foo=1 --foo=2', dict(foo=['1', '2'])),
            ("foo=True", '--foo', dict(foo=False)),
            ("foo=False", '--foo', dict(foo=True)),
            ("foo=False, bar=0", '--bar=10', dict(foo=False, bar=10)),
            ("foo=0, bar=''", '--foo=10 --bar=happy', dict(foo=10, bar='happy')),
        ]

        for test_in, test_out, test_assert in tests:
            script_path = TestScript([
                "#!/usr/bin/env python",
                "def baboom(v): return int(v)",
                "",
                "def main({}):".format(test_in),
                "  return 0"
            ])

            s = Script(script_path)
            if isinstance(test_assert, type) and issubclass(test_assert, Exception):
                with self.assertRaises(test_assert):
                    parser = s.parse()

            else:
                s.parse()
                parser = s.parser
                args, _ = parser.parse_known_args(test_out.split())
                for k, v in test_assert.iteritems():
                    self.assertEqual(v, getattr(args, k))

        # test whether parser knows it shouldn't fail on unknown args
        script_path = TestScript([
            "#!/usr/bin/env python",
            "def main(**kwargs): return 0"
        ])

        s = Script(script_path)
        s.parse()
        self.assertTrue(s.parser.unknown_args)


        # make sure docblock works as description
        desc = 'this is the docblock'
        script_path = TestScript([
            "#!/usr/bin/env python",
            "def main(**kwargs):",
            "  '''{}'''".format(desc),
            "  pass"
        ])

        s = Script(script_path)
        s.parse()
        #parser.print_help()
        self.assertEqual(desc, s.parser.description)

