from subprocess import PIPE, STDOUT, call, check_output, Popen




cmd = "python geo_api/script.py GSE456 out_dir=Studies/GSE456; exit 0"
#cmd = "ls python test2.py; exit 0"
p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)

print(p.stdout.read())
print("done")


