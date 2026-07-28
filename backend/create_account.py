"""
RZWire — admin CLI for account management. Not exposed over HTTP.

Run from the backend/ directory:
  Create a user:      python create_account.py
  Reset a password:   python create_account.py --reset <username-or-email>
"""

import argparse
import getpass

import auth
import database


def main():
    parser = argparse.ArgumentParser(description='Create or reset an RZWire account')
    parser.add_argument('--reset', metavar='USERNAME_OR_EMAIL')
    args = parser.parse_args()
    database.init_db()

    if args.reset:
        user = database.get_user_by_identifier(args.reset)
        if not user:
            print(f"No user found for '{args.reset}'")
            return
        password = getpass.getpass('New password: ')
        if not auth.valid_password(password):
            print('Password must be at least 8 characters.')
            return
        database.set_password(user['id'], auth.hash_password(password))
        print(f"Password updated for '{user['username']}'.")
        return

    username = input('Username: ').strip()
    email = input('Email: ').strip()
    password = getpass.getpass('Password: ')
    if not auth.valid_password(password):
        print('Password must be at least 8 characters.')
        return
    try:
        user = database.create_user(username, email, auth.hash_password(password))
    except ValueError as e:
        print(f'Error: {e}')
        return
    print(f"Created user '{user['username']}' ({user['email']}).")


if __name__ == '__main__':
    main()
