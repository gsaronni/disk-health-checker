watch -n 1 '
for disk in sdf sdh sda sdg sdi; do
    name=$(case $disk in
        sdf) echo "Avicenna";;
        sdh) echo "Zimrilim";;
        sda) echo "Serapeum";;
        sdg) echo "Ashurbanipal";;
        sdi) echo "Elderowl";;
    esac)
    temp=$(smartctl -a /dev/$disk | grep -i "Temp" | awk "END {print \$10}")
    echo "$name Temperature: $temp"
done
'
