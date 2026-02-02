// bot.js
// One-file Discord bot with whitelist + moderation

const { 
    Client, 
    GatewayIntentBits, 
    Partials, 
    Collection, 
    SlashCommandBuilder, 
    REST, 
    Routes 
} = require('discord.js');
const fs = require('fs');
require('dotenv').config();

// ====== CONFIG ======
const TOKEN = process.env.TOKEN;          // Put your bot token in .env as TOKEN=...
const CLIENT_ID = process.env.CLIENT_ID;  // Your bot's application ID
const GUILD_ID = process.env.GUILD_ID;    // Dev server ID for registering commands

// ====== WHITELIST STORAGE ======
const whitelistPath = './whitelist.json';
if (!fs.existsSync(whitelistPath)) {
    fs.writeFileSync(whitelistPath, JSON.stringify({ users: [] }, null, 4));
}
let whitelist = JSON.parse(fs.readFileSync(whitelistPath));

function saveWhitelist() {
    fs.writeFileSync(whitelistPath, JSON.stringify(whitelist, null, 4));
}

function checkWhitelist(userId) {
    return whitelist.users.includes(userId);
}

function addWhitelist(userId) {
    if (!whitelist.users.includes(userId)) {
        whitelist.users.push(userId);
        saveWhitelist();
        return true;
    }
    return false;
}

function removeWhitelist(userId) {
    if (whitelist.users.includes(userId)) {
        whitelist.users = whitelist.users.filter(id => id !== userId);
        saveWhitelist();
        return true;
    }
    return false;
}

// ====== CLIENT SETUP ======
const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMembers,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent
    ],
    partials: [Partials.Channel]
});

client.commands = new Collection();

// ====== COMMAND DEFINITIONS ======
const commands = [];

// /whitelist
const whitelistCommand = new SlashCommandBuilder()
    .setName('whitelist')
    .setDescription('Manage bot whitelist')
    .addSubcommand(sub =>
        sub.setName('add')
            .setDescription('Add a user to whitelist')
            .addUserOption(opt => opt.setName('user').setDescription('User').setRequired(true))
    )
    .addSubcommand(sub =>
        sub.setName('remove')
            .setDescription('Remove a user from whitelist')
            .addUserOption(opt => opt.setName('user').setDescription('User').setRequired(true))
    )
    .addSubcommand(sub =>
        sub.setName('list')
            .setDescription('Show all whitelisted users')
    );

// /ban
const banCommand = new SlashCommandBuilder()
    .setName('ban')
    .setDescription('Ban a member')
    .addUserOption(opt => opt.setName('user').setDescription('User to ban').setRequired(true))
    .addStringOption(opt => opt.setName('reason').setDescription('Reason').setRequired(false));

// /kick
const kickCommand = new SlashCommandBuilder()
    .setName('kick')
    .setDescription('Kick a member')
    .addUserOption(opt => opt.setName('user').setDescription('User to kick').setRequired(true))
    .addStringOption(opt => opt.setName('reason').setDescription('Reason').setRequired(false));

// /timeout
const timeoutCommand = new SlashCommandBuilder()
    .setName('timeout')
    .setDescription('Timeout a member (in minutes)')
    .addUserOption(opt => opt.setName('user').setDescription('User to timeout').setRequired(true))
    .addIntegerOption(opt => opt.setName('minutes').setDescription('Duration in minutes').setRequired(true))
    .addStringOption(opt => opt.setName('reason').setDescription('Reason').setRequired(false));

// /purge
const purgeCommand = new SlashCommandBuilder()
    .setName('purge')
    .setDescription('Delete a number of messages')
    .addIntegerOption(opt => opt.setName('amount').setDescription('1-100').setRequired(true));

// /ping
const pingCommand = new SlashCommandBuilder()
    .setName('ping')
    .setDescription('Check bot latency');

// Push to array for registration
commands.push(
    whitelistCommand,
    banCommand,
    kickCommand,
    timeoutCommand,
    purgeCommand,
    pingCommand
);

// Map commands by name
client.commands.set('whitelist', { data: whitelistCommand });
client.commands.set('ban', { data: banCommand });
client.commands.set('kick', { data: kickCommand });
client.commands.set('timeout', { data: timeoutCommand });
client.commands.set('purge', { data: purgeCommand });
client.commands.set('ping', { data: pingCommand });

// ====== REGISTER SLASH COMMANDS ======
const rest = new REST({ version: '10' }).setToken(TOKEN);

async function registerCommands() {
    try {
        console.log('Registering application commands...');
        await rest.put(
            Routes.applicationGuildCommands(CLIENT_ID, GUILD_ID),
            { body: commands.map(cmd => cmd.toJSON()) }
        );
        console.log('Commands registered.');
    } catch (error) {
        console.error('Error registering commands:', error);
    }
}

// ====== EVENT: READY ======
client.once('ready', () => {
    console.log(`${client.user.tag} is online.`);
});

// ====== EVENT: INTERACTION ======
client.on('interactionCreate', async interaction => {
    if (!interaction.isChatInputCommand()) return;

    const name = interaction.commandName;

    // Whitelist check (except for whitelist command itself)
    if (name !== 'whitelist' && !checkWhitelist(interaction.user.id)) {
        return interaction.reply({
            content: '❌ You are not whitelisted to use this bot.',
            ephemeral: true
        });
    }

    try {
        // ====== WHITELIST COMMAND ======
        if (name === 'whitelist') {
            const sub = interaction.options.getSubcommand();

            // Only allow whitelisting by people already whitelisted (or you can hardcode your ID)
            if (!checkWhitelist(interaction.user.id)) {
                return interaction.reply({
                    content: '❌ You are not allowed to manage the whitelist.',
                    ephemeral: true
                });
            }

            if (sub === 'add') {
                const user = interaction.options.getUser('user');
                const added = addWhitelist(user.id);
                return interaction.reply(
                    added
                        ? `✅ **${user.tag}** has been added to the whitelist.`
                        : `⚠️ **${user.tag}** is already whitelisted.`
                );
            }

            if (sub === 'remove') {
                const user = interaction.options.getUser('user');
                const removed = removeWhitelist(user.id);
                return interaction.reply(
                    removed
                        ? `🗑️ **${user.tag}** has been removed from the whitelist.`
                        : `⚠️ **${user.tag}** is not whitelisted.`
                );
            }

            if (sub === 'list') {
                const list = whitelist.users;
                if (list.length === 0) return interaction.reply('📭 Whitelist is empty.');
                return interaction.reply(
                    `📜 **Whitelisted Users:**\n${list.map(id => `<@${id}>`).join('\n')}`
                );
            }
        }

        // ====== PING ======
        if (name === 'ping') {
            return interaction.reply(`🏓 Pong! Latency: ${Date.now() - interaction.createdTimestamp}ms`);
        }

        // ====== BAN ======
        if (name === 'ban') {
            if (!interaction.member.permissions.has('BanMembers')) {
                return interaction.reply({ content: '❌ You lack **Ban Members** permission.', ephemeral: true });
            }

            const user = interaction.options.getUser('user');
            const reason = interaction.options.getString('reason') || 'No reason provided';

            const member = await interaction.guild.members.fetch(user.id).catch(() => null);
            if (!member) return interaction.reply('❌ Could not find that member.');

            await member.ban({ reason });
            return interaction.reply(`🔨 Banned **${user.tag}** | Reason: ${reason}`);
        }

        // ====== KICK ======
        if (name === 'kick') {
            if (!interaction.member.permissions.has('KickMembers')) {
                return interaction.reply({ content: '❌ You lack **Kick Members** permission.', ephemeral: true });
            }

            const user = interaction.options.getUser('user');
            const reason = interaction.options.getString('reason') || 'No reason provided';

            const member = await interaction.guild.members.fetch(user.id).catch(() => null);
            if (!member) return interaction.reply('❌ Could not find that member.');

            await member.kick(reason);
            return interaction.reply(`👢 Kicked **${user.tag}** | Reason: ${reason}`);
        }

        // ====== TIMEOUT ======
        if (name === 'timeout') {
            if (!interaction.member.permissions.has('ModerateMembers')) {
                return interaction.reply({ content: '❌ You lack **Timeout Members** permission.', ephemeral: true });
            }

            const user = interaction.options.getUser('user');
            const minutes = interaction.options.getInteger('minutes');
            const reason = interaction.options.getString('reason') || 'No reason provided';

            const member = await interaction.guild.members.fetch(user.id).catch(() => null);
            if (!member) return interaction.reply('❌ Could not find that member.');

            const ms = minutes * 60 * 1000;
            await member.timeout(ms, reason);
            return interaction.reply(`⏱️ Timed out **${user.tag}** for **${minutes}** minutes | Reason: ${reason}`);
        }

        // ====== PURGE ======
        if (name === 'purge') {
            if (!interaction.member.permissions.has('ManageMessages')) {
                return interaction.reply({ content: '❌ You lack **Manage Messages** permission.', ephemeral: true });
            }

            const amount = interaction.options.getInteger('amount');
            if (amount < 1 || amount > 100) {
                return interaction.reply({ content: '❌ Amount must be between 1 and 100.', ephemeral: true });
            }

            const messages = await interaction.channel.bulkDelete(amount, true).catch(() => null);
            if (!messages) return interaction.reply('❌ Failed to delete messages (messages may be too old).');

            return interaction.reply(`🧹 Deleted **${messages.size}** messages.`);
        }

    } catch (error) {
        console.error(error);
        if (!interaction.replied) {
            interaction.reply({ content: '❌ An error occurred while executing that command.', ephemeral: true });
        }
    }
});

// ====== START ======
(async () => {
    await registerCommands();
    client.login(TOKEN);
})();
