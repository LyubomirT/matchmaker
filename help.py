helpstr = """
## How to use Matchmaker

Matchmaker is a tool to help you find the best possible match for your collaborative projects. Here's how you can use it as:

### As a Host

1.  Create a profile using the `/profile` command to set up your call name, bio, and available jobs.
2.  Use the `/setjobs` command to add the jobs you can contribute to your profile. You can use autocomplete to find existing jobs in the server.
3.  Create a lobby using the `/createlobby` command to specify a name and description for your project.
4.  Manage your lobby with these commands:
    * `/viewlobbystatus` to see all the lobbies you're currently in.
    * `/lobbyinfo` to view information about a specific lobby, including its members and owner.
    * `/kickfromlobby` to kick a member who is no longer relevant to your project. (**Requires permission!**)
    * `/blockuser` to block a user from joining your lobby in the future. (**Requires permission!**)
    * `/unblockuser` to unblock a previously blocked user. (**Requires permission!**)
    * `/announce` to send a message to all members currently in your lobby.

### As a Job Seeker

1.  Create a profile using the `/profile` command to set up your call name, bio, and available jobs.
2.  Use the `/setjobs` command to add the jobs you can contribute to your profile. You can use autocomplete to find existing jobs in the server.
3.  Use the `/available` command to set your availability for projects (available or not available).
4.  Find a suitable lobby using the `/viewjobs` command to see the list of available jobs in the server and `/mylobbies` to see any lobbies you're already a part of.
5.  Join a lobby using the `/joinlobby` command. You can only join a lobby if there are available slots and you have the required skills (jobs).

### As a Server Admin

1.  Upload a list of available jobs using the `/uploadjobs` command. (**Requires permission!**) This command accepts a `.txt` file containing the job descriptions.
2.  Remove jobs from the server using the `/removelists` command. (**Requires permission!**) This command also accepts a `.txt` file containing the job names to remove.

**Tips:**

* Keep your profile bio up-to-date to showcase your skills and experience.
* Only set yourself as available for projects if you're actively looking for work.
* Be clear and concise when describing your project in your lobby description.
* When creating a lobby, consider the number of members you need for the project and the required skills (jobs).

**Please note:**

* Some commands require permission (creator or server admin) to use.
* This guide covers the core functionalities. Explore the commands for additional features!
"""