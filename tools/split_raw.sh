root_dir=$1
lines_per_file=$2
input_dir=$root_dir/raw
output_dir=$root_dir/split

# 创建输出目录（如果不存在）
mkdir -p "$output_dir"

# 遍历输入目录下的所有文件
for input_file in "$input_dir"/*; do
    # 获取文件的前缀名（不带扩展名）和后缀名
    prefix="$(basename "${input_file%.*}")_"
    extension="${input_file##*.}"

    # 使用 split 命令将文件按指定行数分割，并存入输出目录
    split -l "$lines_per_file" "$input_file" "${output_dir}/${prefix}"

    # 重命名分割后的文件，确保后缀为原始文件的后缀名，并且使用三位数字
    n=1
    for file in "${output_dir}/${prefix}"*; do
        mv "$file" "${output_dir}/${prefix}$(printf '%03d' $n).${extension}"
        n=$((n+1))
    done
done
