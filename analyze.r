library(survival)
library(rms)

typeSmells <- c('max-statements','max-depth','complexity','max-len','max-params','max-nested-callbacks','complex-switch-case','this-assign','complex-chaining','no-reassign','no-extra-bind','cond-assign')

for (ts in typeSmells) {
	f <- paste('Grunt_',ts,'.csv',sep = '')
	if (file.exists(f)) {
		mydata <- read.csv(f)
		attach(mydata)
		kmsurvival <- npsurv(Surv(Time, Event) ~ 1)
		# summary(kmsurvival)
		title_jpeg <- paste('Grunt_',ts,'_rplot.jpg',sep = '')
		jpeg(title_jpeg)
		survplot(kmsurvival, xlab = "Time (in days)", ylab = "Survival Probability")
		dev.off()
		detach(mydata)
	}
}