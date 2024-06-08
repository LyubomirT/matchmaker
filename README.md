# Matchmaker

Orangery Matchmaker is a tool to help collaborators in Discord find each other and team up. It's a Discord bot that allows users to create profiles, specify their skills, and join or create lobbies for collaborative projects.

## Features

- **Profile Management**: Users can create and manage their profiles using the `/profile` command. They can set up their call name, bio, and available jobs.

- **Job Management**: Users can add or remove jobs to their profile using the `/setjobs` and `/removejob` commands respectively. The bot provides autocomplete functionality to find existing jobs in the server.

- **Lobby Management**: Users can create a lobby for their projects using the `/createlobby` command. They can manage their lobbies with commands like `/viewlobbystatus`, `/lobbyinfo`, `/kickfromlobby`, `/blockuser`, `/unblockuser`, and `/announce`.

- **Availability Status**: Users can set their availability for projects using the `/available` command.

- **Joining Lobbies**: Users can join a lobby if there are available slots and they have the required skills using the `/joinlobby` command.

- **Activity Tracking**: The bot tracks user activity and provides a leaderboard of the most active users in the server.

## Setup

1. Clone the repository.
2. Install the required dependencies listed in [`requirements.txt`](requirements.txt).
3. Set up your environment variables in a [`.env`](.env) file. The bot requires a Discord token which should be set as `DISCORD_TOKEN`. You must also provide a MongoDB connection string as `MONGO_URI`.
4. Run [`bot.py`](bot.py) to start the bot.

## License

This project is licensed under the GNU General Public License. For more details, see the [`LICENSE`](LICENSE) file.

## Contributing

Contributions are welcome! Please read the [`LICENSE`](LICENSE) for details on our code of conduct, and the process for submitting pull requests.

## Contact

For more information on how to contact the author, please read the [`LICENSE`](LICENSE) file.

## Acknowledgements

This bot uses the Py-Cord library to interact with the Discord API. For more information, visit the [Py-Cord GitHub repository](https://github.com/Pycord-Development/pycord).