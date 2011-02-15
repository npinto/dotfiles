
if [ -f ~/.bashrc ]; then
   source ~/.bashrc
fi

# ssh keychain / ssh-agent
if [[ -f ~/.bashrc && -f /usr/bin/keychain ]]; then
keychain ~/.ssh/id_rsa;
. ~/.keychain/$HOSTNAME-sh;
fi


