#!/bin/bash
# Check if the script is run as root (admin)
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)."
    exit 1
fi

# Function to get disk temperatures
get_disk_temperatures() {
    # Based on your lsblk output, here are the correct mappings:
    for disk in sda sdb sdc sdd sde sdf sdg sdh sdi sdj sdk; do
        name=$(
        case $disk in
            sda) echo "Slowl";;           # /media/slowl
            sdb) echo "Serapeum";;        # /mnt/serapeum
            sdc) echo "Root";;            # / (root partition)
            sdd) echo "HP120";;           # /media/hp120
            sde) echo "Lil12";;           # /mnt/lil12
            sdf) echo "Grayskull";;       # /media/grayskull
            sdg) echo "Iomega";;          # /media/iomega
            sdh) echo "Avicenna";;        # /mnt/avicenna
            sdi) echo "Ashurbanipal";;    # /mnt/ashurbanipal
            sdj) echo "Zimrilim";;        # /mnt/zimrilim
            sdk) echo "ElderOwl";;        # /mnt/xinyang
        esac)
        
        # Get temperature, handle cases where smartctl might not return temp
        temp=$(smartctl -a /dev/$disk 2>/dev/null | grep -i "Temperature_Celsius\|Current Drive Temperature" | awk '{print $10}' | head -n1)
        
        # If no temperature found, try alternative grep pattern
        if [ -z "$temp" ]; then
            temp=$(smartctl -a /dev/$disk 2>/dev/null | grep -i "temp" | awk '{print $10}' | head -n1)
        fi
        
        # Display result
        if [ -n "$temp" ] && [ "$temp" != "" ]; then
            echo "$name ($disk) Temperature: ${temp}°C"
        else
            echo "$name ($disk) Temperature: N/A"
        fi
    done
}

# Run the function every second
while true; do
    clear
    echo "=== Disk Temperature Monitor ==="
    echo "$(date)"
    echo "================================"
    get_disk_temperatures
    sleep 8
done
