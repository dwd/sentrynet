# SentryNet
#### Abusing Sentry into an Uptime/Responsivity Monitor

### Licence and Copyright

Copyright 2023 Dave Cridland <dave@cridland.net>

This is licensed to you under the highly permissive "MIT" licence,
which is included in full as LICENCE.

For the avoidance of doubt, all source code herein, whether singly
or in aggregate, is under the same copyright and copyright licence
unless specifically stated otherwise at the top of the file.

### What's it do?

SentryNet is a smallish chunk of Python which probes your services in various ways, dumping errors and telemetry into Sentry.

THRILL! To graphs of response times.

![Screenshot of Discover graph](docs/images/discover.png)

GASP! At breakdowns of the probe trace.

![Screenshot of Trace](docs/images/trace.png)

BE DISAPPOINTED! At errors if your services are unreachable.

Obviously I'd put a screenshot here, too, but all my services are perfect and never get downtime.

You'll need:
* A Sentry account, or a self-hosted Sentry deployment.
* One or (ideally) several more places you can run a bit of Python.
* Something to monitor, ideally itself already using Sentry.

### Configuration

SentryNet is configured by a simply YAML file.

It has two sections:

#### Sentry Configuration

The `sentry` top level key contains two sub-keys:
* `dsn` - you'll want to create a new Project in Sentry and put the DSN here.
* `tags` - all subkeys of this will be put as tags against all transactions and events in Sentry. Pick anything (or nothing) you want.

Example:
```yaml
sentry:
  dsn: https://3641121feabb3b0fb5798fba2ae4e215@sentry.cridland.io/238947
  tags:
    location: mission-control
    another.tag: value
```

#### Probe Group Configuration

The only other top-level key is `groups`, which contains a list of probe groups.

These just have another set of `tags` and a list of `probes`.

```yaml
groups:
    - tags:
        target: demo
      probes:
      - probe: probes.http
        url: https://www.google.co.uk/
        every: 30
      - probe: probes.http
        url: https://www.bing.com/
        every: 60
        burst: 4
      - probe: probes.http
        url: https://www.duckduckgo.com/
      - probe: probes.http
        url: http://sentry.io/
```

#### Probe Configuration

These require, at minimum, a `probe` key, which simply points to the Python module that implements the probe.

Optionally, they can include:
* `title` - a title - for some probes that can't default a sensible one, this is mandatory.
* `every` - gives the period in seconds.
* `burst` - how many to do each time. Bursts are consecutive not concurrent.

### Probe Types

#### probes.http

The only defined "production ready" type right now is a relatively simple HTTP probe. It'll do a GET on the URL you give, and check the status code it gets back. This uses two additional keys in the `probe` definition:

* `url` - the (mandatory) URL to probe.
* `method` - the HTTP method (verb) to use. If this isn't set, the default is `GET` unless there's a `body` - in which case it's `POST`
* `expected` - the status code we expect, defaulting to `200` (or `201` for `POST`)
* `body` - optional request body. You can provide a string to send, here, or if this is a map, it'll be JSON encoded.
* `set_keys` - a map of identifiers ("keys") to JSONPATH to extract from the response.
* `assertions` - a map of keys against assertions - currently either `exists` with a boolean, which defaults to true, and `value` with an exact value match.

For example, to test a `/status` endpoint that responds with `{"status":"ok"}` if you post in `{"checks":["status"]}` normally, try:
```yaml
- probe: probes.http
  url: https://api.example/status
  body:
    check:
      - status
  expected: 200
  set_keys:
    status: "$.status"
  assertions:
    status: ok
```

#### probes.script

This is broadly a chained set of the requests above. Keys created by `set_keys` carry
over between requests, and unlike the simple  probe above,
both URLs and request bodies can be interpolated using them.

The overall probe is required to have a `title` set, and optionally has
an `init_keys` mapping, containing each key's initial value.

Finally, a `steps` array has the same keys as the `probes.http` probe's keys above, except:

* Generic probe keys, like `title`, or `every`, are not permitted here.
* `url` and `body` keys are interpolated.

Interpolation operates by the Python `str.format_map`, in fact, with the current keys passed in directly as a map.

However, if a string to be interpolated precisely matches the name of a key, it's simply replaced. Therefore if there is a key called `test` currently set to `true`, and the body looks like:

```yaml
body:
  thing: test
```

Then what'll be sent as the body is actually:

```json
{"thing":true}
```

If you genuinely want the string "test" sent here, then rename the key. 

#### probes.ssh

OpenSSH client, instrumented by reading off the debug log in realtime. Currently does work, but you'd need to make available private keys which seems less than useful; I need to handle the case where we simply want to check service availability without needing credentials and checking we can authenticate. 

### Usage

The simplest thing to do is to put your config.yaml into this directory, build a docker image, and deploy it somewhere for cheap laughs.

Once configured and running, it will simply emit transaction (and error) events to Sentry for its configured Project.

The usual Issues and Performance sections will work as usual, though errors here are (hopefully!) relating to the target of the probe and not SentryNet itself.

You can also build Discover queries and Dashboard out of the data, hopefully quite easily.

The trick to using it effectively is to tag effectively so you can slice the data as needed.
