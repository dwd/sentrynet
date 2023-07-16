import asyncio

import sentry_sdk

from .config import Config


async def probe(config: Config):
    cmd = config.command or 'echo OK'
    ssh = await asyncio.create_subprocess_exec(
        'ssh',
        '-v',
        '%s@%s' % (config.username, config.host),
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    # while True:
    #     try:
    #         text = await asyncio.wait_for(ssh.stderr.read(), config.timeout)
    #         for line in text.split('\n'):
    #             print('SSH line:', repr(line))
    #     except:
    #         break
    with sentry_sdk.Hub.current.start_span(op='ssh', description='response') as top_span:
        span = top_span.start_child(op='ssh.init', description='Initialization')
        while True:
            tmp = await ssh.stderr.readline()
            if not len(tmp):
                break
            if tmp.startswith(b'debug1: '):
                line = tmp[8:].decode().strip()
                if line.startswith('Connecting to'):
                    span.finish()
                    span = top_span.start_child(op='ssh.connect', description=line)
                elif line.startswith('Connection established'):
                    span.finish()
                    span = top_span.start_child(op='ssh.banner', description='Banner exchange')
                elif line.startswith('Authenticating to'):
                    span.finish()
                    span = top_span.start_child(op='ssh.auth', description=line)
                elif line.startswith('Entering interactive session'):
                    span.finish()
                    span = top_span.start_child(op='ssh.exec', description=line)
                elif line.startswith('Sending command'):
                    span.finish()
                    span = top_span.start_child(op='ssh.cmd', description=line)
        span.finish()
    stdin, stdout = await ssh.communicate()
