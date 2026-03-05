"""WebSocket stress test script.

Simulates concurrent WebSocket connections to test server capacity.
Target: 1000 concurrent WebSocket connections for hackathon event.

Usage:
    python -m tests.load.websocket_stress_test --url http://localhost:5000 --users 100
"""
import argparse
import asyncio
import time
import statistics
import sys
from collections import defaultdict

try:
    import socketio as sio_client
except ImportError:
    print('Install python-socketio[asyncio_client]: pip install "python-socketio[asyncio_client]"')
    sys.exit(1)


class StressTestMetrics:
    """Collect and report stress test metrics."""

    def __init__(self):
        self.connect_times = []
        self.message_round_trips = []
        self.errors = defaultdict(int)
        self.connected_count = 0
        self.disconnected_count = 0
        self.messages_sent = 0
        self.messages_received = 0

    def report(self):
        """Print metrics summary."""
        print('\n' + '=' * 60)
        print('WebSocket Stress Test Results')
        print('=' * 60)
        print(f'Connections attempted:    {self.connected_count + self.disconnected_count}')
        print(f'Connections successful:   {self.connected_count}')
        print(f'Disconnections:           {self.disconnected_count}')
        print(f'Messages sent:            {self.messages_sent}')
        print(f'Messages received:        {self.messages_received}')

        if self.connect_times:
            print(f'\nConnection time (ms):')
            print(f'  Min:    {min(self.connect_times):.1f}')
            print(f'  Max:    {max(self.connect_times):.1f}')
            print(f'  Mean:   {statistics.mean(self.connect_times):.1f}')
            print(f'  Median: {statistics.median(self.connect_times):.1f}')
            if len(self.connect_times) > 1:
                print(f'  StdDev: {statistics.stdev(self.connect_times):.1f}')

        if self.message_round_trips:
            print(f'\nMessage round-trip (ms):')
            print(f'  Min:    {min(self.message_round_trips):.1f}')
            print(f'  Max:    {max(self.message_round_trips):.1f}')
            print(f'  Mean:   {statistics.mean(self.message_round_trips):.1f}')
            print(f'  Median: {statistics.median(self.message_round_trips):.1f}')

        if self.errors:
            print(f'\nErrors:')
            for error_type, count in self.errors.items():
                print(f'  {error_type}: {count}')

        print('=' * 60)

        # Pass/fail criteria
        success_rate = (
            self.connected_count /
            max(self.connected_count + len(self.errors), 1)
        ) * 100
        print(f'\nSuccess rate: {success_rate:.1f}%')
        if success_rate >= 95:
            print('PASS: >= 95% connection success rate')
        else:
            print('FAIL: < 95% connection success rate')


async def simulate_user(
    user_id, base_url, session_cookie, metrics, messages_per_user=5
):
    """Simulate a single WebSocket user."""
    client = sio_client.AsyncClient()
    connected_event = asyncio.Event()
    message_received_event = asyncio.Event()

    @client.on('connected')
    async def on_connected(data):
        metrics.connected_count += 1
        connected_event.set()

    @client.on('message_sent')
    async def on_message_sent(data):
        metrics.messages_received += 1
        message_received_event.set()

    @client.on('new_message')
    async def on_new_message(data):
        metrics.messages_received += 1
        message_received_event.set()

    @client.on('error')
    async def on_error(data):
        metrics.errors['socket_error'] += 1

    try:
        # Connect
        start = time.monotonic()
        await client.connect(
            base_url,
            headers={'Cookie': f'hackathon_session={session_cookie}'},
            transports=['websocket'],
        )
        connect_time = (time.monotonic() - start) * 1000
        metrics.connect_times.append(connect_time)

        # Wait for connected event
        await asyncio.wait_for(connected_event.wait(), timeout=10)

        # Join a room
        await client.emit('join_room', {'room': 'channel_general'})

        # Send messages
        for i in range(messages_per_user):
            message_received_event.clear()
            start = time.monotonic()
            await client.emit('send_message', {
                'content': f'Stress test message {i} from user {user_id}',
                'message_type': 'channel',
                'channel_id': 'channel_general',
            })
            metrics.messages_sent += 1

            try:
                await asyncio.wait_for(message_received_event.wait(), timeout=5)
                rt = (time.monotonic() - start) * 1000
                metrics.message_round_trips.append(rt)
            except asyncio.TimeoutError:
                metrics.errors['message_timeout'] += 1

            # Small delay between messages
            await asyncio.sleep(0.1)

        # Stay connected briefly
        await asyncio.sleep(1)

    except Exception as e:
        metrics.errors[type(e).__name__] += 1
    finally:
        if client.connected:
            await client.disconnect()
            metrics.disconnected_count += 1


async def run_stress_test(base_url, num_users, session_cookie, messages_per_user=5):
    """Run the stress test with multiple simulated users."""
    metrics = StressTestMetrics()

    print(f'Starting stress test: {num_users} users, {messages_per_user} messages each')
    print(f'Target: {base_url}')

    # Create user tasks in batches to avoid overwhelming the server
    batch_size = 50
    tasks = []

    for batch_start in range(0, num_users, batch_size):
        batch_end = min(batch_start + batch_size, num_users)
        batch_tasks = [
            simulate_user(i, base_url, session_cookie, metrics, messages_per_user)
            for i in range(batch_start, batch_end)
        ]
        tasks.extend(batch_tasks)

        if batch_start + batch_size < num_users:
            print(f'  Launching batch {batch_start}-{batch_end}...')
            await asyncio.sleep(0.5)  # Brief pause between batches

    print(f'All {num_users} users launching...')
    await asyncio.gather(*tasks, return_exceptions=True)

    metrics.report()
    return metrics


def main():
    parser = argparse.ArgumentParser(description='WebSocket Stress Test')
    parser.add_argument('--url', default='http://localhost:5000', help='Server URL')
    parser.add_argument('--users', type=int, default=100, help='Number of concurrent users')
    parser.add_argument('--messages', type=int, default=5, help='Messages per user')
    parser.add_argument('--cookie', default='', help='Session cookie value')
    args = parser.parse_args()

    if not args.cookie:
        print('Warning: No session cookie provided. Connections may be rejected.')
        print('Use --cookie <session_value> to provide an authenticated session.')

    asyncio.run(run_stress_test(args.url, args.users, args.cookie, args.messages))


if __name__ == '__main__':
    main()
