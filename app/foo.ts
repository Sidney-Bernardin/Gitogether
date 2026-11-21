import bcrypt from "bcryptjs";

console.log(await bcrypt.hash("password", await bcrypt.genSalt(12)))
