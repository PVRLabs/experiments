"""Launch the demo; simple mode removes all Prometheus jars at runtime."""
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
os.chdir(root)
simple = len(sys.argv) > 1 and sys.argv[1] == "simple"
classpath = (root / "target/classpath.txt").read_text().strip().split(os.pathsep)
if simple:
    classpath = [path for path in classpath if "prometheus" not in path.lower()]
java = os.environ.get("DEMO_JAVA", "java")
os.execvp(java, [java, "-cp", os.pathsep.join([str(root / "target/classes"), *classpath]),
                 "example.Application", *( ["simple"] if simple else [])])
