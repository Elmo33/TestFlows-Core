# Copyright 2020 Katteli Inc.
# TestFlows.com Open-Source Software Testing Framework (http://testflows.com)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import re
#import pwd
import base64
import textwrap
import datetime

from collections import OrderedDict

import testflows._core.cli.arg.type as argtype

from testflows._core.cli.arg.common import epilog
from testflows._core.cli.arg.common import HelpFormatter
from testflows._core.cli.arg.handlers.handler import Handler as HandlerBase
from testflows._core.transform.log.pipeline import ResultsLogPipeline
from testflows._core.cli.arg.handlers.report.copyright import copyright
from testflows._core.testtype import TestType
from testflows._core.name import basename, sep
from testflows._core.utils.sort import human
from testflows._core.utils.string import title as make_title

logo = '<img class="logo" src="data:image/png;base64,%(data)s" alt="logo"/>'
testflows = '<span class="testflows-logo"></span> [<span class="logo-test">Test</span><span class="logo-flows">Flows</span>]'
testflows_em = testflows.replace("[", "").replace("]", "")

template = f"""
<section class="clearfix">%(logo)s%(confidential)s%(copyright)s</section>

---
# %(title)s Requirements Traceability Report

## Table of Contents

%(table_of_contents)s

## 1. Overview

This document describes how requirements are linked to the tests. In general,
this relationship is many-to-many where one requirement can be linked to one or
more tests or one test can be linked to one or more requirements.

%(body)s

<br>
---
Generated by {testflows} Open-Source Test Framework

[<span class="logo-test">Test</span><span class="logo-flows">Flows</span>]: https://testflows.com
"""

class Formatter(object):
    def format_logo(self, data):
        if not data["company"].get("logo"):
            return ""
        data = base64.b64encode(data["company"]["logo"]).decode("utf-8")
        return '\n<p>' + logo % {"data": data} + "</p>\n"

    def format_confidential(self, data):
        if not data["company"].get("confidential"):
            return ""
        return f'\n<p class="confidential">Document status - Confidential</p>\n'

    def format_copyright(self, data):
        if not data["company"].get("name"):
            return ""
        return (f'\n<p class="copyright">\n'
            f'{copyright(data["company"]["name"])}\n'
            "</p>\n")

    def format_multiline(self, text, indent=None):
        first, rest = (text.rstrip() + "\n").split("\n", 1)
        first = first.strip()
        if first:
            first += "\n"
        out = f"{first}{textwrap.dedent(rest.rstrip())}".rstrip()
        if indent:
            out = textwrap.indent(out, indent)
        return out

    def format_traceability_table(self, data, toc):
        ss = [""]
        s = []
        s.append("## 2. Traceability Table\n")
        s.append("\n")
        s.append("This section includes requirements traceability table.")
        ss.append("\n".join(s))

        def anchor(heading):
            return re.sub(r"\s+", "-", re.sub(r"[^a-zA-Z0-9-_\s]+", "", heading.lower()))


        names = human(list(data["requirements"].keys()))

        for idx, name in enumerate(names):
            s = []

            rq = data["requirements"][name]
            version = rq["requirement"]["requirement_version"]
            description = rq["requirement"]["requirement_description"]
            tests = rq["tests"]

            s.append(f'<div markdown="1" class="compact stripped" style="font-size: smaller; padding: 1em; border-top: 1px solid #3fdc84; border-bottom: 1px solid #3fdc84; {"border-top: none" if idx != 0 else ""}">')
            s.append(f"### {name}\n")
            heading = s[-1].lstrip("# ").strip()

            s.append(f'version **{version}**')

            s.append("###### DESCRIPTION\n")
            s.append(f'{(description or "").strip()}')
            s.append("\n")

            if tests:
                s.append("###### TESTS\n")
                for test in tests:
                    s.append(f'* {test["test_name"]}  ')
                s.append("\n")

            s.append("</div>")
            ss.append("\n".join(s))

            toc.append(f"{'  '}* [{heading}](#{anchor(heading)})")

        return "\n".join(ss)

    def format(self, data):
        toc = []
        toc.append("* 1 [Overview](#1-overview)")
        toc.append("* 2 [Traceability Table](#2-traceability-table)")
        body = self.format_traceability_table(data, toc)
        return template.strip() % {
            "title": data["title"],
            "table_of_contents": "\n".join(toc),
            "logo": self.format_logo(data),
            "confidential": self.format_confidential(data),
            "copyright": self.format_copyright(data),
            "body": body,
            #"date": f"{datetime.datetime.now():%b %d,%Y}",
            #"author": pwd.getpwuid(os.getuid()).pw_name
        }


class Handler(HandlerBase):
    Formatter = Formatter

    @classmethod
    def add_command(cls, commands):
        parser = commands.add_parser("traceability", help="requirements traceability report", epilog=epilog(),
            description="Generate requirements traceability report.",
            formatter_class=HelpFormatter)

        parser.add_argument("input", metavar="input", type=argtype.logfile("r", bufsize=1, encoding="utf-8"),
                nargs="?", help="input log, default: stdin", default="-")
        parser.add_argument("output", metavar="output", type=argtype.file("w", bufsize=1, encoding="utf-8"),
                nargs="?", help='output file, default: stdout', default="-")
        parser.add_argument("--copyright", metavar="name", help="add copyright notice", type=str)
        parser.add_argument("--confidential", help="mark as confidential", action="store_true")
        parser.add_argument("--logo", metavar="path", type=argtype.file("rb"),
                help='use logo image (.png)')

        parser.set_defaults(func=cls())

    def company(self, args):
        d = {}
        if args.copyright:
            d["name"] = args.copyright
        if args.confidential:
            d["confidential"] = True
        if args.logo:
            d["logo"] = args.logo.read()
        return d

    def title(self, results):
        if results["tests"]:
            title = basename(list(results["tests"].values())[0]["test"]["test_name"])
            if title:
                title = make_title(title)
            return title
        return ""

    def requirements(self, results):
        requirements = OrderedDict()
        for uname, test in results["tests"].items():
            if getattr(TestType, test["test"]["test_type"]) < TestType.Test:
                continue
            for requirement in test["test"]["requirements"]:
                if requirements.get(requirement["requirement_name"]) is None:
                    requirements[requirement["requirement_name"]] = {
                        "requirement": requirement,
                        "tests": []
                    }
                requirements[requirement["requirement_name"]]["tests"].append(test["test"])
        return requirements

    def data(self, results, args):
        d = OrderedDict()
        d["requirements"] = self.requirements(results)
        d["title"] = self.title(results)
        d["company"] = self.company(args)
        return d

    def generate(self, formatter, results, args):
        output = args.output
        output.write(
            formatter.format(self.data(results, args))
        )
        output.write("\n")

    def handle(self, args):
        results = OrderedDict()
        ResultsLogPipeline(args.input, results).run()
        formatter = self.Formatter()
        self.generate(formatter, results, args)
