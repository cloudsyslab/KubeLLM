# update the models used for LLM agents

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <api agent> <debug agent>"
    exit 1
fi

find . -name 'config_step.json' | xargs \
sed -i -e "/\"api-agent\": {/,/}/ s/\(\s*\"model\":\s*\)\".*\"/\1\"$1\"/" \
-e "/\"debug-agent\": {/,/}/ s/\(\s*\"model\":\s*\)\".*\"/\1\"$2\"/"
